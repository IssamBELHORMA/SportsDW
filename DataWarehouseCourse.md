# Data Warehousing — A Practical Course
### Built around the SportsDW project: La Liga Analytics

---

## Table of Contents

1. [What is a Data Warehouse?](#1-what-is-a-data-warehouse)
2. [The Medallion Architecture](#2-the-medallion-architecture)
3. [Phase 1 — Raw Ingestion (Bronze Layer)](#3-phase-1--raw-ingestion-bronze-layer)
4. [Phase 2 — Dimensional Modeling (Gold Layer)](#4-phase-2--dimensional-modeling-gold-layer)
5. [Phase 3 — dbt Transformations](#5-phase-3--dbt-transformations)
6. [Phase 4 — Analytical Queries](#6-phase-4--analytical-queries)
7. [Key Concepts Reference](#7-key-concepts-reference)

---

## 1. What is a Data Warehouse?

A **data warehouse** is a database designed specifically for analytics. It is different from an operational database (like the one behind a web app) in one fundamental way: it is built for reading and aggregating large amounts of historical data, not for inserting or updating individual rows.

### Operational database vs Data warehouse

| | Operational DB | Data Warehouse |
|---|---|---|
| Purpose | Run the application | Answer business questions |
| Operations | INSERT, UPDATE, DELETE | SELECT, GROUP BY, JOIN |
| Data | Current state | Historical records |
| Users | Applications | Analysts, dashboards |
| Example | Match result stored after a game | "How many goals did Barcelona score at home across 4 seasons?" |

### Why not just use CSV files?

You could query CSVs directly — DuckDB even lets you do it. But a warehouse gives you:

- **Schema enforcement** — column types are defined and consistent
- **Queryability** — join multiple seasons, filter, aggregate with full SQL
- **Lineage** — every row knows where it came from and when it was loaded
- **Separation of concerns** — raw data, cleaned data, and analytics-ready data live in distinct layers

### The tool: DuckDB

This project uses **DuckDB** as the warehouse engine. DuckDB is an embedded analytical database — it runs inside your Python process, stores everything in a single `.ddb` file, and speaks standard SQL. It is fast, free, and requires no server setup.

```python
import duckdb

# Connect to (or create) the warehouse
with duckdb.connect("warehouse.ddb") as con:
    con.sql("SELECT 'warehouse is ready'").show()
```

One important constraint: DuckDB only allows **one writer at a time**. If a process has the file open for writing, no other process can open it. Always use `with` blocks to guarantee the connection closes cleanly.

---

## 2. The Medallion Architecture

The medallion architecture organizes your warehouse into three layers, each with a clear purpose. Data flows in one direction: bronze → silver → gold.

```
Source files (CSV)
      ↓
  BRONZE — raw, faithful copy of source data
      ↓
  SILVER — cleaned, standardized, renamed
      ↓
  GOLD  — shaped for analytics (star schema)
```

### Bronze layer

**Rule: land it as-is. Never transform data before it enters bronze.**

Bronze is a faithful copy of your source data. Every column from the source is preserved, even if you'll never use it. Nothing is renamed, nothing is cleaned. If the source has messy column names, nulls, or inconsistent formats — that's what bronze contains.

In this project, bronze holds all 164 columns from the La Liga CSVs, including 140+ betting odds columns you'll never query in analytics.

Why keep all those columns? Because you never know what you'll need later, and storage is cheap. Losing source data is irreversible.

### Silver layer

**Rule: clean and standardize. No business logic yet.**

Silver takes bronze data and makes it trustworthy. Typical silver operations:

- Rename cryptic column names to readable ones (`FTHG` → `home_goals`)
- Fix data types (`Date` string → proper `DATE`)
- Handle nulls
- Deduplicate rows
- Standardize string formats

In this project, silver is a dbt view that selects the 23 useful match columns from bronze, renames them all, and discards the betting data.

### Gold layer

**Rule: shape for analytics. Optimized for the questions you want to answer.**

Gold contains your dimensional model — the star schema. It is stored as physical tables (not views) for fast query performance. This is the layer your dashboards and analysts query.

---

## 3. Phase 1 — Raw Ingestion (Bronze Layer)

### The ingestion script

The ingestion script lives at `ingest/load_bronze.py`. Its job is to:

1. Connect to `warehouse.ddb`
2. Find all CSV files in `data/raw/`
3. Parse the season from each filename
4. Load all files into `bronze.matches_raw` using `UNION ALL BY NAME`
5. Add metadata columns: `season`, `_source_file`, `_loaded_at`

```python
import duckdb
import glob
import os
from datetime import datetime

def extract_season(filename):
    # "LaLiga 25-26.csv" -> "2025-26"
    name = filename.replace("LaLiga ", "").replace(".csv", "")
    parts = name.split("-")
    year_start = "20" + parts[0]
    return f"{year_start}-{parts[1]}"

with duckdb.connect("warehouse.ddb") as con:
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    csv_files = sorted(glob.glob("data/raw/*.csv"))

    union_parts = []
    for filepath in csv_files:
        filename = os.path.basename(filepath)
        season = extract_season(filename)
        loaded_at = datetime.now().isoformat()

        union_parts.append(f"""
            SELECT *, '{season}' AS season,
                   '{filename}' AS _source_file,
                   '{loaded_at}' AS _loaded_at
            FROM read_csv_auto('{filepath}', header=true, union_by_name=true)
        """)

    full_query = "\nUNION ALL BY NAME\n".join(union_parts)
    con.execute(f"CREATE OR REPLACE TABLE bronze.matches_raw AS {full_query}")
```

### Key concepts from Phase 1

**`union_by_name=true`** — when CSV files from different seasons have different columns (schema evolution), this tells DuckDB to match columns by name rather than position. Missing columns are filled with `NULL`. This is the correct way to handle schema changes in a source system.

**`UNION ALL BY NAME`** — reads all files at once, reconciling all column differences before creating the table. Never creates a partial table then inserts into it, which would fail when a new column appears.

**Metadata columns** — `_source_file` and `_loaded_at` are added at load time. They tell you where each row came from and when it was loaded. Prefixed with `_` by convention to signal they are pipeline metadata, not source data.

**Idempotency** — `CREATE OR REPLACE TABLE` means the script is safe to run multiple times. Running it again produces the same result without errors or duplicates. Every pipeline script should be idempotent.

**`sorted()`** — ensures files are always processed in alphabetical (chronological) order regardless of filesystem ordering.

### Verifying the bronze layer

```python
with duckdb.connect("warehouse.ddb") as con:
    # Row count per season
    print(con.sql("""
        SELECT season, COUNT(*) AS matches
        FROM bronze.matches_raw
        GROUP BY season
        ORDER BY season
    """).fetchdf().to_string())

    # Column counts to check schema evolution
    print(con.sql("""
        SELECT season,
               COUNT(*) AS total_matches,
               COUNT(FTHG) AS has_goals,
               COUNT(B365H) AS has_b365_odds
        FROM bronze.matches_raw
        GROUP BY season
        ORDER BY season
    """).fetchdf().to_string())
```

---

## 4. Phase 2 — Dimensional Modeling (Gold Layer)

### The grain

Before designing any table, you must define the **grain**: what does one row represent?

In this project: **one row = one match**. Every design decision flows from this. You never mix two levels of granularity in the same fact table.

### Star schema

A **star schema** is a dimensional model with one fact table at the center surrounded by dimension tables. It gets its name from how it looks in a diagram.

```
         dim_date
            |
dim_team — fact_matches — dim_team
            |
         dim_season
```

**Fact table** — stores measurable events. Contains numbers you'll aggregate (goals, shots, cards) and foreign keys pointing to dimensions. One row per event (match).

**Dimension table** — stores descriptive context. Contains attributes you'll filter and group by (team name, season label, month). One row per entity (team, date, season).

### Why not just query bronze directly?

You could. But there are three problems:

1. **Wrong shape for analytics** — bronze is match-centric. Analytics questions are team-centric or season-centric. Getting per-team stats from bronze requires remembering that `HomeTeam + FTHG` = home goals AND `AwayTeam + FTAG` = away goals, then unioning them. In gold, one clean join handles this.

2. **Cryptic column names** — `FTHG`, `HST`, `AY` require memorization. Gold columns are named `home_goals`, `home_shots_on_target`, `away_yellow_cards`.

3. **No place for metadata** — if you want to add team city or stadium capacity, there's nowhere to put it in bronze. `dim_team` gives you that home.

### The four tables

#### `dim_season`

```sql
CREATE OR REPLACE TABLE gold.dim_season AS
SELECT
    ROW_NUMBER() OVER (ORDER BY season)         AS season_id,
    season                                       AS season_label,
    CAST('20' || LEFT(season, 2) AS INTEGER)     AS start_year,
    CAST('20' || RIGHT(season, 2) AS INTEGER)    AS end_year
FROM (SELECT DISTINCT season FROM bronze.matches_raw)
ORDER BY season
```

**Surrogate key** — `ROW_NUMBER()` generates a synthetic integer primary key. The source data has no natural numeric ID for a season, so you create one. Surrogate keys are standard practice in dimensional modeling because they are stable, compact, and independent of source system changes.

#### `dim_team`

```sql
CREATE OR REPLACE TABLE gold.dim_team AS
SELECT
    ROW_NUMBER() OVER (ORDER BY team_name)  AS team_id,
    team_name
FROM (
    SELECT DISTINCT HomeTeam AS team_name FROM bronze.matches_raw
    UNION
    SELECT DISTINCT AwayTeam AS team_name FROM bronze.matches_raw
)
ORDER BY team_name
```

`UNION` (not `UNION ALL`) deduplicates automatically. A team appearing in multiple seasons gets exactly one row. Teams promoted or relegated across seasons are all included because you scan all seasons.

#### `dim_date`

```sql
CREATE OR REPLACE TABLE gold.dim_date AS
SELECT
    CAST(STRFTIME(full_date, '%Y%m%d') AS INTEGER)  AS date_id,
    full_date,
    EXTRACT(YEAR  FROM full_date)::INTEGER           AS year,
    EXTRACT(MONTH FROM full_date)::INTEGER           AS month,
    EXTRACT(DAY   FROM full_date)::INTEGER           AS day,
    EXTRACT(WEEK  FROM full_date)::INTEGER           AS week_number,
    STRFTIME(full_date, '%A')                        AS day_of_week,
    CASE WHEN STRFTIME(full_date, '%A') IN ('Saturday','Sunday')
         THEN true ELSE false END                    AS is_weekend
FROM (
    SELECT DISTINCT CAST(Date AS DATE) AS full_date
    FROM bronze.matches_raw WHERE Date IS NOT NULL
)
```

**Why a date dimension?** Without it, every query filtering by month needs `EXTRACT(MONTH FROM date) = 12`. With `dim_date`, you write `WHERE month = 12`. The date dimension pre-computes all calendar attributes once so every query benefits automatically.

**Date ID convention** — `YYYYMMDD` as an integer (e.g. `20220812`). Human-readable, sortable, and requires no join to decode. A widely used convention in data warehouses.

#### `fact_matches`

```sql
CREATE OR REPLACE TABLE gold.fact_matches AS
SELECT
    ROW_NUMBER() OVER (ORDER BY m.Date, m.HomeTeam)  AS match_id,
    ds.season_id,
    home.team_id                                      AS team_id_home,
    away.team_id                                      AS team_id_away,
    CAST(STRFTIME(CAST(m.Date AS DATE), '%Y%m%d')
         AS INTEGER)                                  AS date_id,
    m.FTHG   AS home_goals,
    m.FTAG   AS away_goals,
    m.FTR    AS result,
    m.HS     AS home_shots,
    m.HST    AS home_shots_on_target,
    -- ... more stats
FROM bronze.matches_raw m
JOIN gold.dim_season ds   ON m.season    = ds.season_label
JOIN gold.dim_team   home ON m.HomeTeam  = home.team_name
JOIN gold.dim_team   away ON m.AwayTeam  = away.team_name
```

### Role-playing dimension

`dim_team` is joined **twice** in `fact_matches` — once for the home team and once for the away team. This is called a **role-playing dimension**: the same dimension plays two different roles in the same fact row.

```sql
-- Querying the role-playing dimension
SELECT
    home.team_name  AS home_team,
    away.team_name  AS away_team,
    f.home_goals,
    f.away_goals
FROM gold.fact_matches f
JOIN gold.dim_team home ON f.team_id_home = home.team_id
JOIN gold.dim_team away ON f.team_id_away = away.team_id
```

You see this pattern in any domain with multiple references to the same entity: shipping address vs billing address in e-commerce, sender vs recipient in messaging, buyer vs seller in transactions.

### Row count integrity check

After building the gold layer, always verify no rows were lost:

```python
# The correct way — compare counts independently
SELECT
    (SELECT COUNT(*) FROM bronze.matches_raw) AS bronze_rows,
    (SELECT COUNT(*) FROM gold.fact_matches)  AS gold_rows,
    (SELECT COUNT(*) FROM bronze.matches_raw) -
    (SELECT COUNT(*) FROM gold.fact_matches)  AS difference
```

If `difference = 0`, every source row made it through. A non-zero difference means rows were lost in a join, which indicates a mismatch between raw team names and dimension keys.

---

## 5. Phase 3 — dbt Transformations

### What dbt is

**dbt** (data build tool) is the industry-standard framework for the transformation layer of a data warehouse. It does not store data, move data, or connect to source systems. It only does one thing: takes `SELECT` statements and runs them against your database in the right order.

You write this:

```sql
SELECT team_id, team_name FROM {{ ref('silver_matches') }}
```

dbt turns it into:

```sql
CREATE OR REPLACE TABLE gold.dim_team AS
SELECT team_id, team_name FROM silver.silver_matches
```

You focus on the logic. dbt handles materialization, ordering, and documentation.

### The `ref()` function

`{{ ref('model_name') }}` is the most important dbt concept. It does three things:

1. **Declares a dependency** — dbt knows this model depends on `silver_matches` and will always run `silver_matches` first
2. **Resolves the correct schema** — you never hardcode schema names
3. **Builds the lineage graph** — dbt can visualize the full chain from source to gold

Without `ref()`, you manage execution order manually. With it, dbt handles everything automatically.

### Materializations

dbt models can be materialized as views or tables, configured in `dbt_project.yml`:

```yaml
models:
  sportsdw:
    bronze:
      +materialized: view    # instant, no data copied
    silver:
      +materialized: view    # instant, no data copied
    gold:
      +materialized: table   # stored on disk, fast to query
```

**View** — saves the `SELECT` definition. No data is copied. Runs the query fresh every time it's called. Correct for bronze and silver since they're intermediate steps.

**Table** — physically stores the query results. Fast to query. Correct for gold since this is what dashboards and analysts hit repeatedly.

### Project structure

```
dbt/sportsdw/
├── dbt_project.yml          ← project config, materialization settings
├── profiles.yml             ← connection details (lives in ~/.dbt/)
├── models/
│   ├── bronze/
│   │   └── bronze_matches.sql
│   ├── silver/
│   │   └── silver_matches.sql
│   └── gold/
│       ├── dim_season.sql
│       ├── dim_team.sql
│       ├── dim_date.sql
│       ├── fact_matches.sql
│       └── schema.yml       ← tests and documentation
├── macros/
│   └── generate_schema_name.sql
```

### dbt tests

Tests are defined in `schema.yml` and run with `dbt test`. Four built-in test types cover most needs:

```yaml
models:
  - name: fact_matches
    columns:
      - name: match_id
        tests:
          - unique        # no duplicate primary keys
          - not_null      # every row has an ID
      - name: result
        tests:
          - not_null
          - accepted_values:
              arguments:
                values: ['H', 'A', 'D']   # only valid result codes
```

| Test | What it catches |
|---|---|
| `unique` | Duplicate surrogate keys |
| `not_null` | Missing values in critical columns |
| `accepted_values` | Invalid values entering the table |

Running `dbt run && dbt test` rebuilds all models and validates data quality in one command. This is the standard pipeline execution pattern.

### The schema macro

By default, dbt concatenates your target schema with any custom schema, producing `gold_bronze` instead of `bronze`. Override this with a macro in `macros/generate_schema_name.sql`:

```sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

This tells dbt to use schema names exactly as specified, without prepending the default schema.

---

## 6. Phase 4 — Analytical Queries

### Running queries

Queries live in `queries/analytics/` as individual `.sql` files. A single runner script executes any of them:

```python
# run_query.py
import duckdb, sys

query_file = sys.argv[1]
with duckdb.connect("warehouse.ddb", read_only=True) as con:
    with open(query_file, "r", encoding="utf-8") as f:
        sql = f.read().strip().rstrip(";")
    result = con.sql(sql)
    if result is not None:
        print(result.fetchdf().to_string())
```

`read_only=True` allows multiple simultaneous connections, so you can query while dbt has the file open.

### Query patterns

#### Pattern 1 — Aggregating across seasons

```sql
SELECT
    s.season_label,
    COUNT(f.match_id)                            AS total_matches,
    SUM(f.home_goals + f.away_goals)             AS total_goals,
    ROUND(AVG(f.home_goals + f.away_goals), 2)   AS avg_goals_per_match,
    ROUND(100.0 * SUM(CASE WHEN f.result = 'H' THEN 1 ELSE 0 END)
          / COUNT(*), 1)                         AS home_win_pct
FROM gold.fact_matches f
JOIN gold.dim_season s ON f.season_id = s.season_id
GROUP BY s.season_label
ORDER BY s.season_label
```

**La Liga insight:** Goals trended up from 955 (2022-23) to 1024 (2025-26). Home advantage is real: home teams win 44–49% of matches.

#### Pattern 2 — Role-playing dimension for per-team stats

The key challenge: a team appears in every match twice (home and away). You must handle both roles with `CASE WHEN`:

```sql
SELECT
    t.team_name,
    SUM(CASE WHEN f.team_id_home = t.team_id AND f.result = 'H' THEN 1
             WHEN f.team_id_away = t.team_id AND f.result = 'A' THEN 1
             ELSE 0 END)                                        AS wins,
    SUM(CASE WHEN f.team_id_home = t.team_id
             THEN f.home_goals ELSE f.away_goals END)           AS goals_scored
FROM gold.fact_matches f
JOIN gold.dim_team t ON t.team_id IN (f.team_id_home, f.team_id_away)
GROUP BY t.team_id, t.team_name
ORDER BY wins DESC
```

**La Liga insight:** Barcelona leads with 113 wins, Real Madrid second with 106, out of 152 matches each across 4 seasons.

#### Pattern 3 — Defensive SQL with `NULLIF`

When dividing, always protect against division by zero:

```sql
ROUND(100.0 * SUM(wins_home) / NULLIF(COUNT(home_matches), 0), 1) AS home_win_pct
```

`NULLIF(x, 0)` returns `NULL` if `x = 0`, which causes the division to return `NULL` instead of throwing an error.

**La Liga insight:** Barcelona wins 65.8% of away matches — exceptional. Granada won 0% of away matches in their season — inevitable relegation.

#### Pattern 4 — CTEs and window functions

A **CTE** (`WITH ... AS`) names an intermediate result for clarity:

```sql
WITH team_season_stats AS (
    SELECT
        t.team_name,
        s.season_label,
        SUM(...) AS goals_scored,
        RANK() OVER (
            PARTITION BY s.season_label
            ORDER BY SUM(...) DESC
        ) AS rank_in_season
    FROM gold.fact_matches f
    JOIN gold.dim_team   t ON t.team_id IN (f.team_id_home, f.team_id_away)
    JOIN gold.dim_season s ON f.season_id = s.season_id
    GROUP BY t.team_name, s.season_label, t.team_id
)
SELECT * FROM team_season_stats WHERE rank_in_season <= 3
```

`RANK() OVER (PARTITION BY season_label ORDER BY goals DESC)` is a **window function**. It ranks rows within a group (season) without collapsing them — unlike `GROUP BY` which collapses rows into aggregates.

**La Liga insight:** Girona scored 85 goals in 2023-24, finishing above Barcelona — their famous Champions League qualification season confirmed in the data.

---

## 7. Key Concepts Reference

### Architecture concepts

| Concept | Definition |
|---|---|
| **Data warehouse** | A database optimized for analytical queries on historical data |
| **Medallion architecture** | Bronze → Silver → Gold layered data organization |
| **Bronze layer** | Raw, faithful copy of source data. Never transformed |
| **Silver layer** | Cleaned, standardized, renamed. No business logic |
| **Gold layer** | Shaped for analytics. Star schema. What analysts query |
| **ELT** | Extract, Load, Transform — load raw data first, transform inside the warehouse |
| **Idempotency** | A script that produces the same result no matter how many times you run it |

### Dimensional modeling concepts

| Concept | Definition |
|---|---|
| **Grain** | What one row represents. Must be defined before designing any table |
| **Fact table** | Stores measurable events. Contains metrics and foreign keys |
| **Dimension table** | Stores descriptive context. Contains attributes for filtering and grouping |
| **Star schema** | One fact table surrounded by dimension tables |
| **Surrogate key** | A synthetic integer primary key generated by the warehouse (`ROW_NUMBER()`) |
| **Natural key** | The identifier from the source system (e.g. team name) |
| **Role-playing dimension** | One dimension table referenced multiple times in the same fact table (e.g. home team, away team) |
| **Date dimension** | Pre-computes calendar attributes (year, month, week, day of week) so queries never need `EXTRACT()` |
| **Schema evolution** | Source data adding new columns over time. Handled with `union_by_name=true` |

### SQL patterns

| Pattern | Use case |
|---|---|
| `UNION ALL BY NAME` | Combine CSVs with different columns |
| `ROW_NUMBER() OVER (ORDER BY ...)` | Generate surrogate keys |
| `CASE WHEN team_id_home = t.team_id THEN ...` | Handle role-playing dimensions |
| `NULLIF(x, 0)` | Protect against division by zero |
| `WITH cte AS (...)` | Name intermediate results for readable queries |
| `RANK() OVER (PARTITION BY ... ORDER BY ...)` | Rank rows within groups |
| `COUNT(column)` vs `COUNT(*)` | Count non-null values vs count all rows |

### dbt concepts

| Concept | Definition |
|---|---|
| **Model** | A `.sql` file containing a single `SELECT` statement |
| **`ref()`** | Declares a dependency between models, builds lineage graph |
| **Materialization** | How dbt persists a model — `view` or `table` |
| **`dbt run`** | Builds all models in dependency order |
| **`dbt test`** | Runs all data quality tests |
| **`dbt debug`** | Checks connection and configuration |
| **`schema.yml`** | Defines tests and documentation for models |

### DuckDB specifics

| Concept | Detail |
|---|---|
| **File locking** | Only one writer at a time. Use `with` blocks. Use `read_only=True` for queries |
| **`read_csv_auto()`** | Reads a CSV with automatic type inference |
| **`union_by_name=true`** | Match columns by name when reading multiple files |
| **`.fetchdf()`** | Returns query result as a pandas DataFrame |
| **`SHOW ALL TABLES`** | Lists all tables across all schemas |

---

## Project structure

```
sportsdw/
├── .gitignore
├── README.md
├── DATA_WAREHOUSING_COURSE.md    ← this file
├── warehouse.ddb                 ← DuckDB database (gitignored)
├── data/
│   └── raw/                      ← source CSV files (gitignored)
├── ingest/
│   └── load_bronze.py            ← Phase 1: loads CSVs into bronze
├── queries/
│   ├── setup/
│   │   └── create_gold.sql       ← Phase 2: raw SQL star schema creation
│   ├── analytics/
│   │   ├── 01_season_summary.sql
│   │   ├── 02_team_performance.sql
│   │   ├── 03_home_away_advantage.sql
│   │   ├── 04_monthly_goals.sql
│   │   └── 05_top_team_seasons.sql
│   └── run_query.py              ← runs any .sql file against the warehouse
└── dbt/
    └── sportsdw/
        ├── dbt_project.yml
        ├── models/
        │   ├── bronze/
        │   │   └── bronze_matches.sql
        │   ├── silver/
        │   │   └── silver_matches.sql
        │   └── gold/
        │       ├── dim_season.sql
        │       ├── dim_team.sql
        │       ├── dim_date.sql
        │       ├── fact_matches.sql
        │       └── schema.yml
        └── macros/
            └── generate_schema_name.sql
```

---

*Built with DuckDB, dbt, and La Liga match data (football-data.co.uk)*