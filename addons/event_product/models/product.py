# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(selection_add=[
        ('event', 'Event Ticket'),
    ], ondelete={'event': 'set service'})


    def _detailed_type_mapping(self):
        type_mapping = super()._detailed_type_mapping()
        type_mapping['event'] = 'service'
        return type_mapping


class Product(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')
