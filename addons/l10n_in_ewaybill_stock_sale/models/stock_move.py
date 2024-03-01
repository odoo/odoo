# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _compute_ewaybill_price_unit(self):
        super()._compute_ewaybill_price_unit()
        for line in self.filtered(lambda l: l.sale_line_id):
            line.ewaybill_price_unit = line.sale_line_id.price_unit

    def _compute_tax_ids(self):
        super()._compute_tax_ids()
        for line in self.filtered(lambda l: l.sale_line_id):
            line.ewaybill_tax_ids = line.sale_line_id.tax_id
