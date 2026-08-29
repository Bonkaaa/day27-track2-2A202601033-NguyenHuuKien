select
    order_date,
    completed_order_rows
from {{ ref('fct_daily_revenue') }}
where completed_order_rows < 0