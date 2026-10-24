-- 06 market basket: products bought in the same order
--   support    = P(A and B)
--   confidence = P(B | A)
--   lift       = confidence / P(B), above 1 means more often together than by chance
-- only products in at least 1% of orders, to keep the self-join small
create or replace view basket_rules as
with order_items as (
    select distinct invoice, stock_code from sales_lines
),
total as (
    select count(distinct invoice) as n_orders from order_items
),
item_counts as (
    select stock_code, count(*) as n
    from order_items
    group by stock_code
    having count(*) >= 0.01 * (select n_orders from total)
),
pairs as (
    select a.stock_code as item_a, b.stock_code as item_b, count(*) as n_ab
    from order_items as a
    inner join order_items as b on a.invoice = b.invoice and a.stock_code <> b.stock_code
    where a.stock_code in (select stock_code from item_counts)
      and b.stock_code in (select stock_code from item_counts)
    group by a.stock_code, b.stock_code
),
names as (
    select stock_code, arg_max(description, invoice_date) as description
    from sales_lines
    group by stock_code
)
select
    p.item_a,
    na.description as description_a,
    p.item_b,
    nb.description as description_b,
    p.n_ab as orders_together,
    p.n_ab / t.n_orders as support,
    p.n_ab / ca.n as confidence,
    (p.n_ab / ca.n) / (cb.n / t.n_orders) as lift
from pairs as p
cross join total as t
inner join item_counts as ca on ca.stock_code = p.item_a
inner join item_counts as cb on cb.stock_code = p.item_b
inner join names as na on na.stock_code = p.item_a
inner join names as nb on nb.stock_code = p.item_b
where p.n_ab >= 0.005 * t.n_orders
order by lift desc, support desc;
