import numpy as np
import pandas as pd

from retail.segmentation import cluster_customers, name_clusters


def synthetic_rfm(n=300, seed=0):
    rng = np.random.default_rng(seed)
    groups = [(10, 20, 5000), (300, 1, 150), (40, 4, 800)]
    rows = []
    for recency, frequency, monetary in groups:
        rows.append(
            pd.DataFrame(
                {
                    "recency_days": rng.normal(recency, recency * 0.1, n).clip(0),
                    "frequency": rng.poisson(frequency, n).clip(1),
                    "monetary": rng.lognormal(np.log(monetary), 0.2, n),
                }
            )
        )
    frame = pd.concat(rows, ignore_index=True)
    frame["customer_id"] = range(len(frame))
    return frame


def test_clusters_recover_obvious_groups():
    clustered, profile, silhouettes = cluster_customers(synthetic_rfm(), k=3)
    assert len(profile) == 3
    assert profile["customers"].tolist() == [300, 300, 300]
    assert silhouettes[3] == silhouettes.max()
    assert profile.iloc[0]["name"].startswith("High-value")


def test_cluster_names_are_unique():
    profile = pd.DataFrame(
        {
            "median_recency_days": [200, 300],
            "median_frequency": [3, 3],
            "median_monetary": [100, 90],
        },
        index=[0, 1],
    )
    names = name_clusters(profile)
    assert len(set(names.values())) == 2
