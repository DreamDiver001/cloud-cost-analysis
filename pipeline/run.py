import argparse
import sys
from pathlib import Path

import duckdb

from .quality import run_checks

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ["mart_monthly_cost", "mart_tag_coverage", "mart_untagged_resources", "mart_commitments",
           "mart_daily_cost", "mart_anomalies", "mart_always_on", "mart_kpis"]


def build(source: Path, database: str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database)
    con.execute(f"CREATE OR REPLACE TABLE raw_billing AS SELECT * FROM read_csv('{source.as_posix()}', header=true, all_varchar=true)")
    for sql_file in sorted((ROOT / "sql").glob("*.sql")):
        con.execute(sql_file.read_text(encoding="utf-8"))
    return con


def main():
    ap = argparse.ArgumentParser(description="Build the FinOps marts from a FOCUS billing export")
    ap.add_argument("--source", type=Path, default=ROOT / "data" / "focus_billing.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "output")
    args = ap.parse_args()

    args.out.mkdir(exist_ok=True)
    con = build(args.source, str(args.out / "finops.duckdb"))

    failed = False
    print("Data quality")
    for name, ok in run_checks(con):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
        failed |= not ok
    if failed:
        print("\nStopped: fix the data quality problems before publishing the reports.")
        sys.exit(1)

    for table in EXPORTS:
        con.execute(f"COPY {table} TO '{(args.out / (table + '.csv')).as_posix()}' (HEADER, DELIMITER ',')")
    print(f"\n{len(EXPORTS)} tables exported to {args.out.relative_to(ROOT)}/ for Power BI\n")
    for kpi, value in con.execute("SELECT kpi, value FROM mart_kpis").fetchall():
        print(f"  {kpi:<52} {value:>12,.1f}")
    con.close()


if __name__ == "__main__":
    main()
