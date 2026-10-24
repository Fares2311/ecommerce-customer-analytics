-- 05 product concentration: what share of products makes 80% of revenue?
create or replace view product_revenue as
with by_product as (
    select
        stock_code,
        arg_max(description, invoice_date) as description,
        sum(quantity) as units,
        sum(line_revenue) as revenue,
        count(distinct invoice) as orders
    from sales_lines
    group by stock_code
)
select
    *,
    row_number() over (order by revenue desc) as revenue_rank,
    sum(revenue) over (order by revenue desc rows unbounded preceding)
        / sum(revenue) over () as cumulative_revenue_share,
    row_number() over (order by revenue desc) / count(*) over () as cumulative_product_share
from by_product
order by revenue desc;
