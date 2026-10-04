from odoo import models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _show_discount(self):
        if not self:
            return False

        self.ensure_one()
        return self.is_plain_discount
