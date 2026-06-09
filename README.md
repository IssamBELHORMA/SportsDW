# SportsDW — La Liga Data Warehouse

A fully functional data warehouse built from scratch using La Liga match data.
Covers the complete modern data stack: raw ingestion, dimensional modeling, dbt transformations, analytical SQL, and an interactive dashboard.

Built as a learning project to understand data warehousing end to end.

---

## What this project covers

- **Medallion architecture** — bronze, silver, gold layers
- **Dimensional modeling** — star schema with fact and dimension tables
- **ELT pipeline** — extract CSVs, load into DuckDB, transform with dbt
- **dbt** — models, tests, documentation, lineage
- **Analytical SQL** — window functions, CTEs, role-playing dimensions
- **Streamlit dashboard** — league overview, team deep-dive, head to head

---

## Tech stack

| Tool | Role |
|---|---|
| [DuckDB](https://duckdb.org) | Warehouse engine — embedded, file-based, SQL-native |
| [dbt-core](https://docs.getdbt.com) + [dbt-duckdb](https://github.com/duckdb/dbt-duckdb) | Transformation layer |
| Python | Ingestion script |
| Streamlit + Plotly | Dashboard |
| Git | Version control |

---

## Data

Source: [football-data.co.uk](https://www.football-data.co.uk/spainm.php) — La Liga match results.

**Seasons included:** 2022-23, 2023-24, 2024-25, 2025-26
**Rows:** 1520 matches (380 per season)
**Grain:** one row = one match

Each CSV includes match results, half-time scores, shots, fouls, corners, cards, and betting odds from multiple bookmakers.

---

## Project structure

```
sportsdw/
│
├── data/
│   └── raw/                        ← source CSVs (not tracked in git)
│       ├── LaLiga 22-23.csv
│       ├── LaLiga 23-24.csv
│       ├── LaLiga 24-25.csv
│       └── LaLiga 25-26.csv
│
├── ingest/
│   └── load_bronze.py              ← loads all CSVs into bronze.matches_raw
│
├── dbt/
│   └── sportsdw/
│       ├── dbt_project.yml         ← project config, materialization settings
│       ├── models/
│       │   ├── bronze/
│       │   │   └── bronze_matches.sql     ← selects useful columns from raw
│       │   ├── silver/
│       │   │   └── silver_matches.sql     ← cleans and renames all columns
│       │   └── gold/
│       │       ├── dim_season.sql
│       │       ├── dim_team.sql
│       │       ├── dim_date.sql
│       │       ├── fact_matches.sql
│       │       └── schema.yml             ← dbt tests and documentation
│       └── macros/
│           └── generate_schema_name.sql   ← overrides default schema naming
│
├── queries/
│   ├── setup/
│   │   └── create_gold.sql         ← raw SQL to build the star schema manually
│   ├── analytics/
│   │   ├── 01_season_summary.sql
│   │   ├── 02_team_performance.sql
│   │   ├── 03_home_away_advantage.sql
│   │   ├── 04_monthly_goals.sql
│   │   └── 05_top_team_seasons.sql
│   └── run_query.py                ← runs any .sql file against the warehouse
│
├── dashboard/
│   └── app.py                      ← Streamlit dashboard
│
├── DATA_WAREHOUSING_COURSE.md      ← full course notes covering every concept
├── .gitignore
└── README.md
```

---

## How to run

### 1 — Install dependencies

```bash
pip install duckdb dbt-core dbt-duckdb streamlit plotly
```

### 2 — Add source data

Download La Liga CSV files from [football-data.co.uk](https://www.football-data.co.uk/spainm.php) and place them in `data/raw/`. Files should be named `LaLiga YY-YY.csv` (e.g. `LaLiga 23-24.csv`).

### 3 — Load the bronze layer

From the project root:

```bash
python ingest/load_bronze.py
```

This creates `warehouse.ddb` and loads all CSV files into `bronze.matches_raw`.

### 4 — Configure dbt

Edit `~/.dbt/profiles.yml` with the absolute path to your `warehouse.ddb`:

```yaml
sportsdw:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "/absolute/path/to/sportsdw/warehouse.ddb"
      schema: gold
      threads: 1
```

### 5 — Run dbt

From inside `dbt/sportsdw/`:

```bash
dbt run       # builds all models in dependency order
dbt test      # runs all data quality tests
```

Expected output:

```
1 of 6 OK  bronze.bronze_matches
2 of 6 OK  silver.silver_matches
3 of 6 OK  gold.dim_date
4 of 6 OK  gold.dim_season
5 of 6 OK  gold.dim_team
6 of 6 OK  gold.fact_matches

13 of 13 tests passed
```

### 6 — Run analytical queries

From the project root:

```bash
python run_query.py queries/analytics/01_season_summary.sql
python run_query.py queries/analytics/02_team_performance.sql
python run_query.py queries/analytics/03_home_away_advantage.sql
python run_query.py queries/analytics/04_monthly_goals.sql
python run_query.py queries/analytics/05_top_team_seasons.sql
```

### 7 — Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`

---

## Warehouse architecture

```
CSV files (source)
     │
     ▼  Python — ingest/load_bronze.py
bronze.matches_raw          164 columns, 1520 rows, raw
     │
     ▼  dbt view
bronze.bronze_matches       23 columns selected, betting odds discarded
     │
     ▼  dbt view
silver.silver_matches       columns renamed, types cleaned
     │
     ├──▶  gold.dim_season      4 rows   — season_id, season_label, start_year, end_year
     ├──▶  gold.dim_team        26 rows  — team_id, team_name
     ├──▶  gold.dim_date        568 rows — date_id, full_date, year, month, week, day_of_week
     └──▶  gold.fact_matches    1520 rows — one row per match, FK to all dimensions
```

### Star schema

`fact_matches` sits at the center with foreign keys to all three dimensions. `dim_team` is a role-playing dimension — referenced twice in the fact table, once as `team_id_home` and once as `team_id_away`.

---

## Dashboard

Three views available at `http://localhost:8501`:

**League Overview** — season KPIs, goals trend, result distribution by season, full season table.

**Team Deep-Dive** — filter by team and season. Win/draw/loss breakdown, goals for vs against, home vs away split, full match log.

**Head to Head** — pick any two teams. Win banner, goals comparison, win share donut, radar chart of average match stats, full match history.

---

## Key insights from the data

- Goals trended up across 4 seasons: 955 → 1005 → 995 → 1024
- Home teams win 44–49% of matches depending on the season
- Barcelona leads all-time with 113 wins from 152 matches (74.3% win rate)
- Girona scored 85 goals in 2023-24, finishing above Barcelona — their Champions League season
- Barcelona wins 65.8% of away matches — the highest in the dataset
- Granada won 0% of away matches in their season

---

## Learning resources

See `DATA_WAREHOUSING_COURSE.md` in this repo for a full course covering every concept used in this project: medallion architecture, dimensional modeling, star schemas, dbt, and analytical SQL patterns — all explained through the decisions made building SportsDW.

---

## Data source

Match data from [football-data.co.uk](https://www.football-data.co.uk) — free historical football results for research and educational use.