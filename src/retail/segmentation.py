"""K-means on log-scaled RFM features.

Used to check the rule-based RFM segments (sql/04_rfm.sql) against the groups the data
finds on its own.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

FEATURES = ["recency_days", "frequency", "monetary"]


def rfm_matrix(rfm: pd.DataFrame) -> np.ndarray:
    """log1p for the long tails of frequency and revenue, then standardise."""
    return StandardScaler().fit_transform(np.log1p(rfm[FEATURES].to_numpy(dtype=float)))


def choose_k(X: np.ndarray, k_values=range(2, 9), seed: int = 42) -> pd.Series:
    scores = {}
    for k in k_values:
        labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(X)
        scores[k] = silhouette_score(X, labels, sample_size=min(len(X), 4000), random_state=seed)
    return pd.Series(scores, name="silhouette")


def name_clusters(profile: pd.DataFrame) -> dict[int, str]:
    """Name each cluster from its median recency, frequency and revenue."""
    names = {}
    value_rank = profile["median_monetary"].rank(ascending=False)
    for cluster, row in profile.iterrows():
        active = row["median_recency_days"] <= 90
        if value_rank[cluster] == 1:
            tier = "High-value"
        elif row["median_frequency"] <= 1.5:
            tier = "One-time"
        else:
            tier = "Mid-value"
        names[cluster] = f"{tier}, {'active' if active else 'lapsed'}"
    seen: dict[str, int] = {}
    # make duplicate names unique, e.g. "Mid-value, lapsed (2)"
    for cluster, name in names.items():
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            names[cluster] = f"{name} ({seen[name]})"
    return names


def cluster_customers(rfm: pd.DataFrame, k: int | None = None, seed: int = 42):
    X = rfm_matrix(rfm)
    silhouettes = choose_k(X, seed=seed)
    if k is None:
        # 2 groups is too coarse to be useful for marketing
        k = int(silhouettes[silhouettes.index >= 3].idxmax())
    labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(X)
    clustered = rfm.assign(cluster=labels)
    profile = clustered.groupby("cluster").agg(
        customers=("customer_id", "size"),
        median_recency_days=("recency_days", "median"),
        median_frequency=("frequency", "median"),
        median_monetary=("monetary", "median"),
        revenue=("monetary", "sum"),
    )
    profile["revenue_share"] = profile["revenue"] / profile["revenue"].sum()
    names = name_clusters(profile)
    profile.insert(0, "name", profile.index.map(names))
    clustered["cluster_name"] = clustered["cluster"].map(names)
    return clustered, profile.sort_values("revenue", ascending=False), silhouettes
