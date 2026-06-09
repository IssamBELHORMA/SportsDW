import duckdb
import sys

query_file = sys.argv[1]

with duckdb.connect("warehouse.ddb", read_only=True) as con:
    with open(query_file, "r", encoding="utf-8") as f:
        sql = f.read().strip().rstrip(";")
    
    result = con.sql(sql)
    
    if result is not None:
        print(result.fetchdf().to_string())
    else:
        print("Query executed but returned no results.")