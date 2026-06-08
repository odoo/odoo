# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import SQL


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _select_pos_dict(self, table):
        order_rate = self._case_value_or_one(table.order_id.currency_rate)
        subtotal = SQL("SIGN(%s) * SIGN(%s) * ABS(%s)", table.qty, table.price_unit, table.price_subtotal)
        return super()._select_pos_dict(table) | {
            'margin': SQL('SUM((%s - COALESCE(%s, 0)) / %s)', subtotal, table.total_cost, order_rate),
            'margin_percent': SQL('MAX(CASE COALESCE(%s, 0) WHEN 0 THEN 0 ELSE (%s - COALESCE(%s, 0)) / (%s) END)', subtotal, subtotal, table.total_cost, subtotal),
            'purchase_price': SQL('SUM(%s / %s)', table.total_cost, order_rate),
        }
