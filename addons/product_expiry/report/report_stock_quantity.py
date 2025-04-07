# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportStockQuantity(models.Model):
    _inherit = 'report.stock.quantity'

    _depends = {
        'stock.quant': ['removal_date'],
    }

    def _get_product_qty_col(self):
        return "CASE WHEN q.removal_date IS NOT NULL AND q.removal_date::date <= (now() at time zone 'utc')::date THEN q.reserved_quantity ELSE q.quantity END"
