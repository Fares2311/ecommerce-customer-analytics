"""Paths and constants."""

import os
from pathlib import Path


def _project_root() -> Path:
    """Use RETAIL_ROOT if set, otherwise walk up to the folder with sql/ and pyproject.toml."""
    if os.getenv("RETAIL_ROOT"):
        return Path(os.environ["RETAIL_ROOT"])
    for folder in [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]:
        if (folder / "sql").is_dir() and (folder / "pyproject.toml").exists():
            return folder
    return Path.cwd()


PROJECT_ROOT = _project_root()
DATA_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
XLSX_PATH = RAW_DIR / "online_retail_II.xlsx"
PARQUET_PATH = RAW_DIR / "transactions.parquet"
SQL_DIR = PROJECT_ROOT / "sql"
REPORTS_DIR = PROJECT_ROOT / "reports"
RESULTS_DIR = REPORTS_DIR / "results"
FIGURES_DIR = REPORTS_DIR / "figures"
