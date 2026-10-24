-- 02 monthly KPIs: revenue, returns, orders, customers, new vs. returning
create or replace view monthly_kpis as
with lines as (
    select
        invoice_month,
        sum(line_revenue) filter (where not is_return) as gross_revenue,
        -sum(line_revenue) filter (where is_return) as returns_value,
        count(distinct invoice) filter (where not is_return) as all_orders
    from transactions_clean
    group by invoice_month
),
customer_orders as (
    select
        o.order_month,
        count(*) as identified_orders,
        count(distinct o.customer_id) as active_customers,
        count(distinct o.customer_id) filter (where o.order_month = c.cohort_month)
            as new_customers,
        sum(o.order_value) filter (where o.order_month > c.cohort_month) as returning_revenue,
        sum(o.order_value) as identified_revenue,
        avg(o.order_value) as avg_order_value
    from orders as o
    inner join customers as c using (customer_id)
    group by o.order_month
)
select
    l.invoice_month,
    l.gross_revenue,
    coalesce(l.returns_value, 0) as returns_value,
    l.gross_revenue - coalesce(l.returns_value, 0) as net_revenue,
    coalesce(l.returns_value, 0) / l.gross_revenue as return_rate,
    l.all_orders,
    c.active_customers,
    c.new_customers,
    c.active_customers - c.new_customers as returning_customers,
    c.avg_order_value,
    coalesce(c.returning_revenue, 0) / c.identified_revenue as returning_revenue_share,
    -- data ends on 2011-12-09, so December 2011 is incomplete
    l.invoice_month < date '2011-12-01' as is_complete_month
from lines as l
left join customer_orders as c on c.order_month = l.invoice_month
order by l.invoice_month;
