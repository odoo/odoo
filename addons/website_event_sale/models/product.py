# -*- coding: utf-8 -*-

from odoo import api, fields, models


# defined for access rules
class Product(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')

    @api.depends('is_event_ticket')
    def _compute_hide_from_shop(self):
        super()._compute_hide_from_shop()
        for product in self:
            product.hide_from_shop = product.hide_from_shop or product.is_event_ticket

    def _is_add_to_cart_allowed(self):
        # Allow adding event tickets to the cart regardless of product's rules
        self.ensure_one()
        res = super()._is_add_to_cart_allowed()
        return res or any(event.website_published for event in self.event_ticket_ids.event_id)
