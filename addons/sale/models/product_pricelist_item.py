from odoo import api, models


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    @api.model
    def _is_discount_feature_enabled(self):
        return self.env['res.groups']._is_feature_enabled('sale.group_discount_per_so_line')

    def _show_discount(self):
        if not self:
            return False

        self.ensure_one()
        return self._is_discount_feature_enabled() and self.compute_price == 'percentage'
