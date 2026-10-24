-- 08 revenue by country (identified customers)
create or replace view country_summary as
select
    country,
    count(distinct customer_id) as customers,
    count(*) as orders,
    sum(order_value) as revenue,
    avg(order_value) as avg_order_value,
    count(*) / count(distinct customer_id) as orders_per_customer,
    sum(order_value) / sum(sum(order_value)) over () as revenue_share
from orders
group by country
order by revenue desc;
