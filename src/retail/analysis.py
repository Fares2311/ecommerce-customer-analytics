"""Run the SQL analyses with DuckDB and export the results."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from retail.config import PARQUET_PATH, RESULTS_DIR, SQL_DIR

logger = logging.getLogger(__name__)

EXPORTED_VIEWS = [
    "monthly_kpis",
    "cohort_retention",
    "retention_curve",
    "rfm_segments",
    "rfm_segment_summary",
    "product_revenue",
    "basket_rules",
    "cohort_cumulative_value",
    "customer_concentration",
    "country_summary",
]


def connect(source: Path | pd.DataFrame = PARQUET_PATH, sql_dir: Path = SQL_DIR):
    """Open an in-memory DuckDB database with all the analysis views.

    `source` is the Parquet file, or a small DataFrame in the tests. The same SQL runs on both.
    """
    con = duckdb.connect()
    if isinstance(source, pd.DataFrame):
        con.register("raw_source", source)
        con.execute("create view raw_transactions as select * from raw_source")
    else:
        con.execute(f"create view raw_transactions as select * from read_parquet('{source}')")
    for path in sorted(sql_dir.glob("*.sql")):
        con.execute(path.read_text(encoding="utf-8"))
        logger.debug("Applied %s", path.name)
    return con


def export_results(con, out_dir: Path = RESULTS_DIR) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for view in EXPORTED_VIEWS:
        frame = con.execute(f"select * from {view}").df()
        frame.to_csv(out_dir / f"{view}.csv", index=False, float_format="%.6g")
        results[view] = frame
        logger.info("%-26s %7d rows", view, len(frame))
    return results


def data_quality_report(con) -> pd.DataFrame:
    """How many raw lines each cleaning rule removes."""
    return con.execute(
        """
        with raw as (select * from raw_transactions),
        dedup as (select distinct * from raw)
        select 'raw lines' as step, count(*) as lines from raw
        union all select 'exact duplicates removed', (select count(*) from raw) - count(*)
            from dedup
        union all select 'bad-debt adjustments (A invoices)', count(*) from dedup
            where invoice like 'A%'
        union all select 'non-product codes (postage, fees, vouchers...)', count(*) from dedup
            where invoice not like 'A%'
              and not (regexp_matches(stock_code, '^[0-9]{5}') or stock_code like 'DCGS%')
        union all select 'zero or negative price', count(*) from dedup
            where invoice not like 'A%' and unit_price <= 0
              and (regexp_matches(stock_code, '^[0-9]{5}') or stock_code like 'DCGS%')
        union all select 'clean lines (sales + returns)', count(*) from transactions_clean
        union all select '  of which returns (C invoices)', count(*) from transactions_clean
            where is_return
        union all select '  of which without customer id', count(*) from transactions_clean
            where customer_id is null
        """
    ).df()
