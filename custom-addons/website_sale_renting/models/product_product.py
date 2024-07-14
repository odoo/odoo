# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _website_show_quick_add(self):
        self.ensure_one()
        website = self.env['website'].get_current_website()
        return super()._website_show_quick_add() or (
            self.rent_ok and (not website.prevent_zero_price_sale or self._get_contextual_price())
        )

    def _is_add_to_cart_allowed(self):
        self.ensure_one()
        return super()._is_add_to_cart_allowed() or (self.active and self.rent_ok and self.website_published)
