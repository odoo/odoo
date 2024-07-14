# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard
from . import populate


def _pre_init_sale_subscription(env):
    """ Allow installing sale_subscription in databases with large sale.order / sale.order.line tables.
    The different sale_subscription fields are all NULL (falsy) for existing sale orders,
    the computation is way more efficient in SQL than in Python.
    """
    env.cr.execute("""
        ALTER TABLE "sale_order_line"
        ADD COLUMN "parent_line_id" int4
    """)
    env.cr.execute("""
        ALTER TABLE "sale_order"
        ADD COLUMN "is_subscription" bool,
        ADD COLUMN  "payment_exception" bool,
        ADD COLUMN  "close_reason_id" int4,
        ADD COLUMN  "subscription_state" varchar,
        ADD COLUMN  "rating_last_value" double precision,
        ADD COLUMN  "end_date" date,
        ADD COLUMN  "payment_token_id" int4,
        ADD COLUMN  "kpi_1month_mrr_delta" double precision,
        ADD COLUMN  "kpi_1month_mrr_percentage" double precision,
        ADD COLUMN  "kpi_3months_mrr_delta" double precision,
        ADD COLUMN  "kpi_3months_mrr_percentage" double precision,
        ADD COLUMN  "percentage_satisfaction" int4,
        ADD COLUMN  "health" varchar,
        ADD COLUMN  "origin_order_id" int4,
        ADD COLUMN  "subscription_id" int4,
        ADD COLUMN  "recurring_monthly" numeric
    """)
