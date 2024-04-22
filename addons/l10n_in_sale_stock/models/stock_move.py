# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _l10n_in_get_product_price_unit(self):
        self.ensure_one()
        if self.sale_line_id:
            return self.sale_line_id.price_unit
        return super()._l10n_in_get_product_price_unit()

    def _l10n_in_get_product_tax(self):
        self.ensure_one()
        if self.sale_line_id:
            return self.sale_line_id.tax_id
        return super()._l10n_in_get_product_tax()
