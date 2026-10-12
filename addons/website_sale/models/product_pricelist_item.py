# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _show_discount_on_shop(self):
        """Whether the shop should strike through the price the discount was taken from.

        The base must be a price the customer could have seen, so a cost is never shown.

        Only for /shop, /product, and configurators, not on the cart or the checkout.
        """
        if not self:
            return False

        self.ensure_one()

        return self._is_discount_rule() and self.base in ("list_price", "pricelist")
