# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportStockQuantity(models.Model):
    _inherit = 'report.stock.quantity'

    _depends = {
        'stock.quant': ['removal_date'],
    }

    def _get_product_qty_col(self):
        # In case the quant is 'to be removed', only count the ones that are reserved as still being fresh
        return "CASE WHEN q.removal_date IS NOT NULL AND q.removal_date::date <= (now() at time zone 'utc')::date AND date >= (now() at time zone 'utc')::date THEN q.reserved_quantity ELSE q.quantity END"
