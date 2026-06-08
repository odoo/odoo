# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class SaleReport(models.Model):
    _inherit = "sale.report"

    margin = fields.Float("Margin", readonly=True)
    margin_percent = fields.Float("Margin (%)", aggregator=None, readonly=True)
    purchase_price = fields.Float(string="Expected Cost", readonly=True)

    def _select_dict(self, table):
        order_rate = self._case_value_or_one(table.order_id.currency_rate)
        rate = SQL("%s / %s", table.consolidation_rate, order_rate)
        return super()._select_dict(table) | {
            'margin': SQL("SUM(%s * %s)", table.margin, rate),
            'margin_percent': SQL("MAX(%s)", table.margin_percent),
            'purchase_price': SQL("CASE WHEN COALESCE(%s, false) = false IS NOT NULL THEN SUM((%s * %s) * %s) ELSE 0 END", table.is_downpayment, table.purchase_price, table.product_uom_qty, rate),
        }
