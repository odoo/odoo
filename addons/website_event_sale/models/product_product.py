# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')

    def _is_add_to_cart_allowed(self, line_id=None, event_ticket_id=None, **kwargs):
        # Allow adding event tickets to the cart regardless of product's rules
        if event_ticket_id:
            return any(event.website_published for event in self.event_ticket_ids.event_id)
        return super()._is_add_to_cart_allowed(event_ticket_id=event_ticket_id, **kwargs) or (
            line_id and any(event.website_published for event in self.event_ticket_ids.event_id)
        )

    def _is_allow_zero_price(self):
        return super()._is_allow_zero_price() or self.is_slide_channel
