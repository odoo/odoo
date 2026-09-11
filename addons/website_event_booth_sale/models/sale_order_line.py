# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _must_drop_from_cart(self):
        """Override of `website_sale` to keep booth lines, as booth products aren't published."""
        return super()._must_drop_from_cart() and not self.event_booth_registration_ids
