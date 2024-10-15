# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons import event_sale, website_sale


# defined for access rules
class ProductProduct(website_sale.ProductProduct):

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')

    def _is_add_to_cart_allowed(self):
        # Allow adding event tickets to the cart regardless of product's rules
        self.ensure_one()
        res = super()._is_add_to_cart_allowed()
        return res or any(event.website_published for event in self.event_ticket_ids.event_id)


class ProductTemplate(event_sale.ProductTemplate, website_sale.ProductTemplate):

    @api.model
    def _get_product_types_allow_zero_price(self):
        return super()._get_product_types_allow_zero_price() + ["event"]
