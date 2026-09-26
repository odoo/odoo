# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id.display_name', 'event_ticket_id.display_name')
    def _compute_name_short(self):
        """ Override of `website_sale` to replace the product name with the ticket name. """
        super()._compute_name_short()

        for line in self:
            if line.event_ticket_id:
                line.name_short = line.event_ticket_id.display_name

    def _should_show_strikethrough_price(self):
        """ Override of `website_sale` to hide the strikethrough price for events. """
        return super()._should_show_strikethrough_price() and not self.event_id

    def _is_custom_cart_line(self):
        # Event ticket lines should not be modified during the ecommerce checkout.
        return super()._is_custom_cart_line() or bool(self.event_id) or bool(self.event_ticket_id)
