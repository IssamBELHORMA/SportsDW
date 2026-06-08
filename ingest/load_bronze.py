import duckdb
import glob
import os
from datetime import datetime

def extract_season(filename):
    name = filename.replace("LaLiga ", "").replace(".csv", "")
    parts = name.split("-")
    year_start = "20" + parts[0]
    return f"{year_start}-{parts[1]}"

with duckdb.connect("warehouse.ddb") as con:

    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    csv_files = sorted(glob.glob("data/raw/*.csv"))

    if not csv_files:
        print("No CSV files found in data/raw/")
        exit()

    print(f"Found {len(csv_files)} file(s) to load...\n")

    # Build a UNION ALL of all files, each tagged with its season metadata
    union_parts = []
    for filepath in csv_files:
        filename = os.path.basename(filepath)
        season = extract_season(filename)
        loaded_at = datetime.now().isoformat()
        print(f"  Staging {filename}  ->  season {season}...")

        union_parts.append(f"""
            SELECT
                *,
                '{season}'    AS season,
                '{filename}'  AS _source_file,
                '{loaded_at}' AS _loaded_at
            FROM read_csv_auto('{filepath}', header=true, union_by_name=true)
        """)

    full_query = "\nUNION ALL BY NAME\n".join(union_parts)

    print("\n  Creating bronze.matches_raw...")
    con.execute(f"""
        CREATE OR REPLACE TABLE bronze.matches_raw AS
        {full_query}
    """)

    print("\n--- Verification ---\n")

    print("Tables in warehouse:")
    print(con.sql("SHOW ALL TABLES").fetchdf().to_string())

    print("\nRow count per season:")
    print(con.sql("""
        SELECT season, _source_file, COUNT(*) AS matches
        FROM bronze.matches_raw
        GROUP BY season, _source_file
        ORDER BY season
    """).fetchdf().to_string())

    print("\nTotal column count in bronze table:")
    print(con.sql("""
        SELECT COUNT(*) AS total_columns
        FROM information_schema.columns
        WHERE table_schema = 'bronze'
        AND table_name = 'matches_raw'
    """).fetchdf().to_string())

    print("\nSample rows (core columns only):")
    print(con.sql("""
        SELECT season, Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR
        FROM bronze.matches_raw
        ORDER BY season, Date
        LIMIT 5
    """).fetchdf().to_string())

print("\nBronze layer ready. Connection closed.")