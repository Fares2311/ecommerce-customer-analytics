import pytest

from retail.analysis import data_quality_report

from .conftest import query


def test_cleaning_rules(con):
    clean = query(con, "select * from transactions_clean")
    assert len(clean) == 11  # 16 raw - 1 duplicate - postage - zero price - adjustment - voucher
    assert not clean["stock_code"].isin(["POST", "B", "gift_0001_20"]).any()
    assert (clean["unit_price"] > 0).all()
    assert clean["is_return"].sum() == 1


def test_data_quality_report_accounts_for_every_line(con):
    report = data_quality_report(con).set_index("step")["lines"]
    assert report["raw lines"] == 16
    assert report["exact duplicates removed"] == 1
    assert report["clean lines (sales + returns)"] == 11


def test_customer_net_revenue_includes_returns(con):
    customers = query(con, "select * from customers order by customer_id").set_index("customer_id")
    assert customers.loc[2, "gross_revenue"] == 46  # 20*2 + 2*3
    assert customers.loc[2, "returned_value"] == -10
    assert customers.loc[2, "net_revenue"] == 36
    assert customers.loc[1, "orders"] == 3
    assert str(customers.loc[3, "cohort_month"])[:7] == "2011-02"


def test_monthly_kpis(con):
    kpis = query(con, "select * from monthly_kpis").set_index("invoice_month")
    january = kpis.iloc[0]
    assert january["gross_revenue"] == 35 + 46  # duplicate line counted once
    assert january["returns_value"] == 10
    assert january["new_customers"] == 2
    february = kpis.iloc[1]
    assert february["new_customers"] == 1 and february["returning_customers"] == 1
    march = kpis.iloc[2]
    assert march["gross_revenue"] == 6  # guest order only


def test_cohort_retention(con):
    cohorts = query(con, "select * from cohort_retention")
    january = cohorts[cohorts["cohort_month"].astype(str).str.startswith("2011-01")]
    rates = dict(zip(january["months_since_first"], january["retention_rate"], strict=True))
    assert rates == {0: 1.0, 1: 0.5, 3: 0.5}  # customer 1 of 2 came back in Feb and Apr


def test_rfm_segments(con):
    rfm = query(con, "select * from rfm_segments").set_index("customer_id")
    assert set(rfm.index) == {1, 2, 3}
    assert rfm.loc[1, "recency_days"] == 1  # ordered on the last day; measured from the next
    assert rfm["r_score"].between(1, 5).all() and rfm["f_score"].between(1, 5).all()
    assert rfm.loc[1, "segment"] != rfm.loc[2, "segment"]


def test_market_basket_metrics(con):
    rules = query(con, "select * from basket_rules")
    red_blue = rules[(rules["item_a"] == "10001") & (rules["item_b"] == "10002")].iloc[0]
    # 7 orders; RED MUG in 5, BLUE MUG in 3, both in 3
    assert red_blue["support"] == pytest.approx(3 / 7)
    assert red_blue["confidence"] == pytest.approx(3 / 5)
    assert red_blue["lift"] == pytest.approx((3 / 5) / (3 / 7))


def test_pareto_is_cumulative(con):
    products = query(con, "select * from product_revenue")
    assert products["cumulative_revenue_share"].is_monotonic_increasing
    assert products["cumulative_revenue_share"].iloc[-1] == pytest.approx(1.0)
