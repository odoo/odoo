# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models      # noqa
from . import report      # noqa

from odoo.tools.sql import column_exists, create_column


def _pre_init_hook(env):
    """Fill the margin columns in SQL on first install.

    sale.order.line / sale.order can hold millions of rows. When a stored computed
    field's column doesn't exist yet, the ORM recomputes it for all records, which
    loads them in memory. If the columns exist and are filled before the module
    is loaded, no recomputation is triggered.
    """
    cr = env.cr
    fill_lines = not column_exists(cr, 'sale_order_line', 'margin')
    for column in ('purchase_price', 'margin', 'margin_percent'):
        if not column_exists(cr, 'sale_order_line', column):
            create_column(cr, 'sale_order_line', column, 'float8')

    if fill_lines:
        # Mirrors SaleOrderLine._compute_purchase_price and _compute_margin.
        # Lines missing company_id / currency_id fall back to the order's values,
        # so no line is skipped and left NULL.
        cr.execute("""
            UPDATE sale_order_line sol
               SET purchase_price = c.cost,
                   margin = c.base - c.cost * c.qty,
                   margin_percent = CASE WHEN c.base <> 0
                                         THEN (c.base - c.cost * c.qty) / c.base
                                         ELSE 0.0 END
              FROM (
                SELECT l.id,
                       CASE WHEN l.product_id IS NULL THEN 0.0 ELSE
                            COALESCE((pp.standard_price ->> COALESCE(l.company_id, so.company_id)::text)::float8, 0.0)
                            * CASE WHEN uom_p.id IS NOT NULL AND uom_l.id IS NOT NULL
                                        AND uom_p.id <> uom_l.id
                                        AND uom_p.category_id = uom_l.category_id
                                   THEN uom_p.factor / uom_l.factor
                                   ELSE 1.0 END
                            * CASE WHEN COALESCE(l.currency_id, so.currency_id) IS NOT NULL
                                        AND rc.currency_id IS NOT NULL
                                        AND COALESCE(l.currency_id, so.currency_id) <> rc.currency_id
                                   THEN COALESCE(rate_to.rate, 1.0) / COALESCE(rate_from.rate, 1.0)
                                   ELSE 1.0 END
                       END AS cost,
                       CASE WHEN COALESCE(l.qty_delivered, 0) <> 0
                                 AND COALESCE(l.product_uom_qty, 0) = 0
                            THEN l.price_unit * l.qty_delivered
                            ELSE COALESCE(l.price_subtotal, 0) END AS base,
                       CASE WHEN COALESCE(l.qty_delivered, 0) <> 0
                                 AND COALESCE(l.product_uom_qty, 0) = 0
                            THEN l.qty_delivered
                            ELSE COALESCE(l.product_uom_qty, 0) END AS qty
                  FROM sale_order_line l
             LEFT JOIN sale_order so ON so.id = l.order_id
             LEFT JOIN res_company rc ON rc.id = COALESCE(l.company_id, so.company_id)
             LEFT JOIN product_product pp ON pp.id = l.product_id
             LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
             LEFT JOIN uom_uom uom_p ON uom_p.id = pt.uom_id
             LEFT JOIN uom_uom uom_l ON uom_l.id = l.product_uom
             -- Rate lookup: latest rate on or before the order date, else the
             -- earliest rate, else 1.0 (via the COALESCEs above). Company-specific
             -- rates win over generic ones.
             LEFT JOIN LATERAL (
                    SELECT r.rate FROM res_currency_rate r
                     WHERE r.currency_id = rc.currency_id
                       AND (r.company_id IS NULL OR r.company_id = rc.id)
                     ORDER BY (r.name <= so.date_order::date) DESC,
                              r.company_id,
                              CASE WHEN r.name <= so.date_order::date THEN r.name END DESC NULLS LAST,
                              r.name ASC
                     LIMIT 1
                   ) rate_from ON COALESCE(l.currency_id, so.currency_id) <> rc.currency_id
             LEFT JOIN LATERAL (
                    SELECT r.rate FROM res_currency_rate r
                     WHERE r.currency_id = COALESCE(l.currency_id, so.currency_id)
                       AND (r.company_id IS NULL OR r.company_id = rc.id)
                     ORDER BY (r.name <= so.date_order::date) DESC,
                              r.company_id,
                              CASE WHEN r.name <= so.date_order::date THEN r.name END DESC NULLS LAST,
                              r.name ASC
                     LIMIT 1
                   ) rate_to ON COALESCE(l.currency_id, so.currency_id) <> rc.currency_id
              ) c
             WHERE c.id = sol.id
        """)

    fill_orders = not column_exists(cr, 'sale_order', 'margin')
    if fill_orders:
        create_column(cr, 'sale_order', 'margin', 'numeric')       # Monetary
    if not column_exists(cr, 'sale_order', 'margin_percent'):
        create_column(cr, 'sale_order', 'margin_percent', 'float8')

    if fill_orders:
        # Mirrors SaleOrder._compute_margin
        cr.execute("""
            UPDATE sale_order so
               SET margin = m.margin,
                   margin_percent = CASE WHEN so.amount_untaxed <> 0
                                         THEN (m.margin / so.amount_untaxed)::float8
                                         ELSE 0.0 END
              FROM (
                SELECT o.id,
                       ROUND(COALESCE(t.total, 0.0)::numeric,
                             COALESCE(cur.decimal_places, 2)) AS margin
                  FROM sale_order o
             LEFT JOIN res_currency cur ON cur.id = o.currency_id
             LEFT JOIN (SELECT order_id, SUM(margin) AS total
                          FROM sale_order_line
                         GROUP BY order_id) t ON t.order_id = o.id
              ) m
             WHERE so.id = m.id
        """)
