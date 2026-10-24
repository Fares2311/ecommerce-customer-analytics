-- 03 cohort retention: cohort = month of first order, then the share of each cohort that
-- orders again in each later month
create or replace view cohort_retention as
with activity as (
    select distinct
        c.cohort_month,
        o.customer_id,
        date_diff('month', c.cohort_month, o.order_month) as months_since_first
    from orders as o
    inner join customers as c using (customer_id)
),
cohort_size as (
    select cohort_month, count(*) as customers
    from activity
    where months_since_first = 0
    group by cohort_month
)
select
    a.cohort_month,
    s.customers as cohort_customers,
    a.months_since_first,
    count(*) as active_customers,
    count(*) / s.customers as retention_rate
from activity as a
inner join cohort_size as s using (cohort_month)
group by a.cohort_month, s.customers, a.months_since_first
order by a.cohort_month, a.months_since_first;

-- average retention curve weighted by cohort size, using only months that are fully observed
create or replace view retention_curve as
select
    months_since_first,
    sum(active_customers) / sum(cohort_customers) as retention_rate,
    count(*) as cohorts
from cohort_retention
where cohort_month + to_months(months_since_first) < date '2011-12-01'
group by months_since_first
order by months_since_first;
