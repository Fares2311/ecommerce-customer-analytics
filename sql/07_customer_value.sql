-- 07 cumulative revenue per customer by months since first order, for each cohort
create or replace view cohort_cumulative_value as
with monthly as (
    select
        c.cohort_month,
        date_diff('month', c.cohort_month, o.order_month) as months_since_first,
        sum(o.order_value) as revenue
    from orders as o
    inner join customers as c using (customer_id)
    group by 1, 2
),
sizes as (
    select cohort_month, count(*) as cohort_customers from customers group by 1
)
select
    m.cohort_month,
    s.cohort_customers,
    m.months_since_first,
    sum(m.revenue) over (
        partition by m.cohort_month order by m.months_since_first
    ) / s.cohort_customers as cumulative_revenue_per_customer
from monthly as m
inner join sizes as s using (cohort_month)
order by m.cohort_month, m.months_since_first;

-- share of net revenue from the top 1% / 10% / 20% / 50% of customers
create or replace view customer_concentration as
with ranked as (
    select
        net_revenue,
        percent_rank() over (order by net_revenue desc) as pct_rank
    from customers
    where net_revenue > 0
)
select
    top_share,
    sum(net_revenue) filter (where pct_rank < top_share) / sum(net_revenue) as revenue_share
from ranked, (values (0.01), (0.10), (0.20), (0.50)) as t(top_share)
group by top_share
order by top_share;
