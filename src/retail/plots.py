"""Report figures."""

from __future__ import annotations

import string
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

BLUE, ORANGE, GREEN, GREY, RED, PURPLE = (
    "#2563eb",
    "#f97316",
    "#16a34a",
    "#9ca3af",
    "#dc2626",
    "#7c3aed",
)
plt.rcParams.update(
    {
        "figure.dpi": 120,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "font.size": 10,
    }
)


def _gbp(x, _=None) -> str:
    return f"£{x / 1e6:.1f}M" if abs(x) >= 1e6 else f"£{x / 1e3:.0f}k"


def plot_monthly(kpis: pd.DataFrame, path: Path) -> None:
    kpis = kpis.copy()
    kpis["label"] = pd.to_datetime(kpis["invoice_month"]).dt.strftime("%b\n%Y")
    x = np.arange(len(kpis))
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 2]}
    )
    colors = [BLUE if c else GREY for c in kpis["is_complete_month"]]
    top.bar(x, kpis["net_revenue"], color=colors)
    top.yaxis.set_major_formatter(_gbp)
    top.set_title("Net revenue per month (grey = partial month: data ends 9 Dec 2011)")
    bottom.bar(x, kpis["returning_customers"], color=BLUE, label="Returning customers")
    bottom.bar(
        x,
        kpis["new_customers"],
        bottom=kpis["returning_customers"],
        color=ORANGE,
        label="New customers",
    )
    bottom.set_title("Active customers per month")
    bottom.legend(loc="upper left")
    bottom.set_xticks(x, kpis["label"], fontsize=7.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_cohort_heatmap(cohorts: pd.DataFrame, path: Path, months: int = 12) -> None:
    grid = cohorts[cohorts["months_since_first"] <= months].pivot(
        index="cohort_month", columns="months_since_first", values="retention_rate"
    )
    grid.index = pd.to_datetime(grid.index).strftime("%Y-%m")
    sizes = cohorts.drop_duplicates("cohort_month").set_index("cohort_month")["cohort_customers"]
    sizes.index = pd.to_datetime(sizes.index).strftime("%Y-%m")
    grid.index = [f"{m}  (n={sizes[m]:,})" for m in grid.index]
    fig, ax = plt.subplots(figsize=(12, 9))
    sns.heatmap(
        grid.drop(columns=0),
        annot=True,
        fmt=".0%",
        cmap="Blues",
        vmin=0,
        vmax=0.45,
        cbar_kws={"format": "{x:.0%}"},
        ax=ax,
        annot_kws={"size": 7.5},
    )
    ax.set(
        title="Monthly cohort retention: share of each cohort ordering again",
        xlabel="Months since first order",
        ylabel="Cohort (first order month)",
    )
    fig.savefig(path)
    plt.close(fig)


def plot_rfm(summary: pd.DataFrame, path: Path) -> None:
    data = summary.sort_values("revenue_share")
    y = np.arange(len(data))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(y + 0.2, data["customer_share"], 0.4, color=GREY, label="Share of customers")
    ax.barh(y - 0.2, data["revenue_share"], 0.4, color=BLUE, label="Share of revenue")
    for yi, value in zip(y, data["revenue_share"], strict=True):
        ax.text(value + 0.005, yi - 0.2, f"{value:.0%}", va="center", fontsize=8)
    ax.set_yticks(y, data["segment"])
    ax.xaxis.set_major_formatter("{x:.0%}")
    ax.set_title("RFM segments: customers vs. revenue")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    fig.savefig(path)
    plt.close(fig)


def plot_pareto(products: pd.DataFrame, path: Path) -> None:
    share_80 = products.loc[
        products["cumulative_revenue_share"] >= 0.8, "cumulative_product_share"
    ].iloc[0]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(
        products["cumulative_product_share"], products["cumulative_revenue_share"], color=BLUE, lw=2
    )
    ax.plot([0, 1], [0, 1], "--", color=GREY, lw=1, label="Equal contribution")
    ax.axhline(0.8, color=ORANGE, lw=1, ls=":")
    ax.axvline(share_80, color=ORANGE, lw=1, ls=":")
    ax.annotate(
        f"{share_80:.0%} of products\n= 80% of revenue",
        (share_80, 0.8),
        xytext=(share_80 + 0.08, 0.55),
        arrowprops={"arrowstyle": "->"},
    )
    ax.xaxis.set_major_formatter("{x:.0%}")
    ax.yaxis.set_major_formatter("{x:.0%}")
    ax.set(
        title=f"Product revenue concentration ({len(products):,} products)",
        xlabel="Share of products (ranked by revenue)",
        ylabel="Cumulative share of revenue",
    )
    ax.legend(loc="lower right")
    fig.savefig(path)
    plt.close(fig)


def top_unique_pairs(rules: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    """Rules exist in both directions (A->B and B->A), keep one row per pair."""
    key = rules.apply(lambda r: tuple(sorted((r["item_a"], r["item_b"]))), axis=1)
    return rules.assign(pair=key).drop_duplicates("pair").head(n)


def _short(description: str, width: int = 34) -> str:
    text = string.capwords(description)
    return text if len(text) <= width else text[: width - 1] + "…"


def plot_basket(rules: pd.DataFrame, path: Path) -> None:
    top = top_unique_pairs(rules).iloc[::-1]
    labels = [
        f"{_short(a)}  +  {_short(b)}"
        for a, b in zip(top["description_a"], top["description_b"], strict=True)
    ]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(labels, top["lift"], color=PURPLE)
    for i, (lift, conf) in enumerate(zip(top["lift"], top["confidence"], strict=True)):
        ax.text(lift + 0.5, i, f"lift {lift:.0f} · conf. {conf:.0%}", va="center", fontsize=8)
    ax.set(
        title="Products most often bought together (lift = times more likely than chance)",
        xlabel="Lift",
    )
    ax.margins(x=0.25)
    ax.grid(axis="y", visible=False)
    fig.savefig(path)
    plt.close(fig)


def plot_clv(cumulative: pd.DataFrame, path: Path) -> None:
    data = cumulative.copy()
    data["cohort_month"] = pd.to_datetime(data["cohort_month"])
    selected = data[
        data["cohort_month"].dt.month.isin([1, 4, 7, 10]) & (data["cohort_month"].dt.year == 2010)
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = [BLUE, GREEN, ORANGE, RED]
    for color, (cohort, group) in zip(colors, selected.groupby("cohort_month"), strict=False):
        group = group[group["months_since_first"] <= 18]
        ax.plot(
            group["months_since_first"],
            group["cumulative_revenue_per_customer"],
            marker="o",
            ms=3,
            color=color,
            label=f"{cohort:%b %Y} cohort",
        )
    ax.yaxis.set_major_formatter("£{x:,.0f}")
    ax.set(
        title="Cumulative revenue per acquired customer",
        xlabel="Months since first order",
        ylabel="Revenue per customer",
    )
    ax.legend()
    fig.savefig(path)
    plt.close(fig)


def plot_clusters(clustered: pd.DataFrame, silhouettes: pd.Series, path: Path) -> None:
    fig, (ax, ax_k) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [3, 1]})
    palette = [BLUE, ORANGE, GREEN, RED, PURPLE, GREY, "#0891b2", "#be185d"]
    for color, (name, group) in zip(palette, clustered.groupby("cluster_name"), strict=False):
        ax.scatter(
            group["recency_days"] + 1,
            group["monetary"],
            s=6,
            alpha=0.5,
            color=color,
            label=f"{name} (n={len(group):,})",
        )
    ax.set(
        xscale="log",
        yscale="log",
        xlabel="Days since last order (log)",
        ylabel="Net revenue per customer, £ (log)",
        title="K-means customer clusters on log-scaled RFM",
    )
    ax.legend(markerscale=3, fontsize=8)
    ax_k.plot(silhouettes.index, silhouettes.values, marker="o", color=BLUE)
    ax_k.set(title="Choosing k", xlabel="Number of clusters", ylabel="Silhouette score")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
