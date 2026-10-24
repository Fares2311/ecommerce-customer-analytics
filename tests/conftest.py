"""Hand-made invoice lines that cover each cleaning rule and the edge cases."""

from __future__ import annotations

import pandas as pd
import pytest

from retail.analysis import connect

COLUMNS = [
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "unit_price",
    "customer_id",
    "country",
]

ROWS = [
    # customer 1: orders in Jan, Feb and Apr 2011 -> retained in months 1 and 3
    ("100001", "10001", "RED MUG", 10, "2011-01-05 10:00", 2.0, 1, "United Kingdom"),
    ("100001", "10002", "BLUE MUG", 5, "2011-01-05 10:00", 3.0, 1, "United Kingdom"),
    (
        "100001",
        "10002",
        "BLUE MUG",
        5,
        "2011-01-05 10:00",
        3.0,
        1,
        "United Kingdom",
    ),  # exact duplicate
    ("100002", "10001", "RED MUG", 4, "2011-02-10 09:00", 2.0, 1, "United Kingdom"),
    ("100002", "10002", "BLUE MUG", 4, "2011-02-10 09:00", 3.0, 1, "United Kingdom"),
    ("100003", "10003", "GREEN BAG", 1, "2011-04-01 12:00", 10.0, 1, "United Kingdom"),
    # customer 2: one January order, partly returned
    ("100004", "10001", "RED MUG", 20, "2011-01-20 15:00", 2.0, 2, "France"),
    ("100004", "10002", "BLUE MUG", 2, "2011-01-20 15:00", 3.0, 2, "France"),
    ("C100005", "10001", "RED MUG", -5, "2011-01-25 15:00", 2.0, 2, "France"),
    # customer 3: February cohort, orders twice in February
    ("100006", "10003", "GREEN BAG", 2, "2011-02-02 11:00", 10.0, 3, "Germany"),
    ("100007", "10001", "RED MUG", 1, "2011-02-20 11:00", 2.0, 3, "Germany"),
    # guest checkout without a customer id: counts as revenue, not in customer analyses
    ("100008", "10001", "RED MUG", 3, "2011-03-03 08:00", 2.0, None, "United Kingdom"),
    # lines every cleaning rule must remove
    ("100009", "POST", "POSTAGE", 1, "2011-03-03 08:00", 18.0, 1, "United Kingdom"),
    ("100010", "10001", "RED MUG", 1, "2011-03-04 08:00", 0.0, 1, "United Kingdom"),
    ("A100011", "B", "Adjust bad debt", 1, "2011-03-05 08:00", 11062.06, None, "United Kingdom"),
    ("100012", "gift_0001_20", "GIFT VOUCHER", 1, "2011-03-06 08:00", 20.0, 2, "France"),
]


@pytest.fixture(scope="session")
def raw() -> pd.DataFrame:
    frame = pd.DataFrame(ROWS, columns=COLUMNS)
    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"])
    frame["customer_id"] = frame["customer_id"].astype("Int64")
    return frame


@pytest.fixture(scope="session")
def con(raw):
    return connect(raw)


def query(con, sql: str) -> pd.DataFrame:
    return con.execute(sql).df()
