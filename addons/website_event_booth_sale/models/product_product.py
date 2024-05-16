# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_add_to_cart_allowed(self, line_id=None, event_booth_pending_ids=None, **kwargs):
        # `event_booth_registration_confirm` calls `_cart_update` with specific products, allow those aswell.
        if event_booth_pending_ids:
            return self.is_event_booth
        return super()._is_add_to_cart_allowed(
            event_booth_pending_ids=event_booth_pending_ids, **kwargs,
        ) or (line_id and self.is_event_booth)  # In case of line increate/decrease from the cart page

    def _is_allow_zero_price(self):
        return super()._is_allow_zero_price() or self.is_event_booth
