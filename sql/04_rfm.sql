-- 04 RFM segmentation
--   recency   = days since the last order (counted from the day after the last transaction)
--   frequency = number of orders
--   monetary  = net revenue (orders minus returns); customers at <= 0 are left out
-- each score is a quintile from 1 to 5 (5 = best). about a third of customers ordered once,
-- so frequency ties are broken by revenue. segment names follow the usual R x F grid.
create or replace view rfm_scores as
with base as (
    select
        customer_id,
        country,
        date_diff('day', cast(last_order_ts as date),
                  (select max(invoice_day) + 1 from transactions_clean)) as recency_days,
        orders as frequency,
        net_revenue as monetary
    from customers
    where net_revenue > 0
)
select
    *,
    6 - ntile(5) over (order by recency_days, frequency desc) as r_score,
    ntile(5) over (order by frequency, monetary) as f_score,
    ntile(5) over (order by monetary) as m_score
from base;

create or replace view rfm_segments as
select
    *,
    case
        when r_score = 5 and f_score >= 4 then 'Champions'
        when r_score between 3 and 4 and f_score >= 4 then 'Loyal Customers'
        when r_score >= 4 and f_score between 2 and 3 then 'Potential Loyalists'
        when r_score = 5 and f_score = 1 then 'New Customers'
        when r_score = 4 and f_score = 1 then 'Promising'
        when r_score = 3 and f_score = 3 then 'Need Attention'
        when r_score = 3 and f_score <= 2 then 'About to Sleep'
        when r_score <= 2 and f_score = 5 then 'Cannot Lose Them'
        when r_score <= 2 and f_score between 3 and 4 then 'At Risk'
        else 'Hibernating'
    end as segment
from rfm_scores;

create or replace view rfm_segment_summary as
select
    segment,
    count(*) as customers,
    count(*) / sum(count(*)) over () as customer_share,
    sum(monetary) as revenue,
    sum(monetary) / sum(sum(monetary)) over () as revenue_share,
    median(recency_days) as median_recency_days,
    median(frequency) as median_orders,
    median(monetary) as median_revenue
from rfm_segments
group by segment
order by revenue desc;
