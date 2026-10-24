"""Download Online Retail II and convert it to Parquet once.

The source is a 45 MB Excel file with one sheet per year. Reading it takes about a minute,
the Parquet file loads in milliseconds.
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import pandas as pd
import requests

from retail.config import DATA_URL, PARQUET_PATH, XLSX_PATH

logger = logging.getLogger(__name__)

COLUMNS = {
    "Invoice": "invoice",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
}


def download(dest: Path = XLSX_PATH, url: str = DATA_URL) -> Path:
    if dest.exists():
        return dest
    logger.info("Downloading %s", url)
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(archive.read("online_retail_II.xlsx"))
    return dest


def to_parquet(xlsx: Path = XLSX_PATH, dest: Path = PARQUET_PATH) -> Path:
    if dest.exists():
        return dest
    download(xlsx)
    logger.info("Converting %s to Parquet (about a minute)", xlsx.name)
    sheets = pd.read_excel(xlsx, sheet_name=None, dtype={"Invoice": str, "StockCode": str})
    frame = pd.concat(sheets.values(), ignore_index=True).rename(columns=COLUMNS)
    frame["customer_id"] = frame["customer_id"].astype("Int64")
    frame["description"] = frame["description"].astype("string").str.strip()
    frame.to_parquet(dest, index=False)
    logger.info("Wrote %d rows to %s", len(frame), dest)
    return dest
