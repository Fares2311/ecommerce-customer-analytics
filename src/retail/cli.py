"""`retail run`: download the data, run the SQL, cluster customers and make the figures."""

from __future__ import annotations

import argparse
import json
import logging

import pandas as pd

from retail import plots
from retail.analysis import connect, data_quality_report, export_results
from retail.config import FIGURES_DIR, PARQUET_PATH, REPORTS_DIR, RESULTS_DIR
from retail.data import to_parquet
from retail.segmentation import cluster_customers

logger = logging.getLogger("retail")


def run() -> dict:
    to_parquet()
    con = connect(PARQUET_PATH)
    quality = data_quality_report(con)
    results = export_results(con, RESULTS_DIR)
    quality.to_csv(RESULTS_DIR / "data_quality.csv", index=False)

    rfm = results["rfm_segments"]
    clustered, profile, silhouettes = cluster_customers(rfm)
    profile.to_csv(RESULTS_DIR / "kmeans_profile.csv")
    crosstab = pd.crosstab(clustered["segment"], clustered["cluster_name"], normalize="index")
    crosstab.to_csv(RESULTS_DIR / "rfm_vs_kmeans.csv", float_format="%.3f")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plots.plot_monthly(results["monthly_kpis"], FIGURES_DIR / "monthly_kpis.png")
    plots.plot_cohort_heatmap(results["cohort_retention"], FIGURES_DIR / "cohort_retention.png")
    plots.plot_rfm(results["rfm_segment_summary"], FIGURES_DIR / "rfm_segments.png")
    plots.plot_pareto(results["product_revenue"], FIGURES_DIR / "product_pareto.png")
    plots.plot_basket(results["basket_rules"], FIGURES_DIR / "market_basket.png")
    plots.plot_clv(results["cohort_cumulative_value"], FIGURES_DIR / "customer_value.png")
    plots.plot_clusters(clustered, silhouettes, FIGURES_DIR / "kmeans_clusters.png")

    kpis = results["monthly_kpis"]
    complete = kpis[kpis["is_complete_month"]]
    segments = results["rfm_segment_summary"].set_index("segment")
    products = results["product_revenue"]
    concentration = results["customer_concentration"].set_index("top_share")["revenue_share"]
    curve = results["retention_curve"].set_index("months_since_first")["retention_rate"]
    summary = {
        "clean_lines": int(
            quality.loc[quality["step"] == "clean lines (sales + returns)", "lines"].iloc[0]
        ),
        "net_revenue": float(kpis["net_revenue"].sum()),
        "customers": int(len(rfm)),
        "orders": int(kpis["all_orders"].sum()),
        "best_month": str(complete.loc[complete["net_revenue"].idxmax(), "invoice_month"]),
        "return_rate": float(kpis["returns_value"].sum() / kpis["gross_revenue"].sum()),
        "retention_month_1": float(curve[1]),
        "retention_month_12": float(curve[12]),
        "champions_customer_share": float(segments.loc["Champions", "customer_share"]),
        "champions_revenue_share": float(segments.loc["Champions", "revenue_share"]),
        "product_share_for_80pct_revenue": float(
            products.loc[
                products["cumulative_revenue_share"] >= 0.8, "cumulative_product_share"
            ].iloc[0]
        ),
        "top_10pct_customers_revenue_share": float(concentration[0.10]),
        "kmeans_k": int(len(profile)),
        "silhouette_by_k": {int(k): round(float(v), 3) for k, v in silhouettes.items()},
    }
    (REPORTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(prog="retail", description=__doc__)
    parser.add_argument("command", choices=["run"])
    parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(run(), indent=2, default=str))


if __name__ == "__main__":
    main()
