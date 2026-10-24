-- 01 staging: clean the raw invoice lines and build the orders / customers views.
-- raw_transactions is registered by the Python runner (Parquet file, or a DataFrame in tests).
--
-- cleaning rules (tested in tests/test_sql.py):
--   - drop exact duplicate lines (~34k)
--   - drop 'A' invoices (bad-debt adjustments)
--   - keep product codes only (5 digits, or DCGS...): drops postage, fees, vouchers, tests
--   - drop unit price <= 0
--   - keep 'C' invoices (returns) as negative quantities so cancelled orders net out
--     (one customer ordered 80,995 units and cancelled 12 minutes later)

create or replace view transactions_clean as
with deduplicated as (
    select distinct * from raw_transactions
)
select
    invoice,
    stock_code,
    description,
    quantity,
    invoice_date,
    cast(invoice_date as date) as invoice_day,
    date_trunc('month', invoice_date)::date as invoice_month,
    unit_price,
    quantity * unit_price as line_revenue,
    customer_id,
    country,
    invoice like 'C%' as is_return
from deduplicated
where invoice not like 'A%'
  and unit_price > 0
  and quantity <> 0
  and (regexp_matches(stock_code, '^[0-9]{5}') or stock_code like 'DCGS%');

-- sales lines only (no returns)
create or replace view sales_lines as
select * from transactions_clean where not is_return and quantity > 0;

-- one row per order, identified customers only
create or replace view orders as
select
    invoice,
    customer_id,
    any_value(country) as country,
    min(invoice_date) as order_ts,
    min(invoice_month) as order_month,
    count(*) as lines,
    sum(quantity) as units,
    sum(line_revenue) as order_value
from sales_lines
where customer_id is not null
group by invoice, customer_id;

-- one row per customer with lifetime totals
create or replace view customers as
select
    o.customer_id,
    arg_min(o.country, o.order_ts) as country,
    min(o.order_ts) as first_order_ts,
    max(o.order_ts) as last_order_ts,
    min(o.order_month) as cohort_month,
    count(*) as orders,
    sum(o.order_value) as gross_revenue,
    coalesce(r.returned_value, 0) as returned_value,
    sum(o.order_value) + coalesce(r.returned_value, 0) as net_revenue
from orders as o
left join (
    select customer_id, sum(line_revenue) as returned_value
    from transactions_clean
    where is_return and customer_id is not null
    group by customer_id
) as r using (customer_id)
group by o.customer_id, r.returned_value;
