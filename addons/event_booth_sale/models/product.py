# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(selection_add=[
        ('event_booth', 'Event Booth'),
    ], ondelete={'event_booth': 'set service'})

    @api.onchange('detailed_type')
    def _onchange_type_event_booth(self):
        if self.detailed_type == 'event_booth':
            self.invoice_policy = 'order'

    def _detailed_type_mapping(self):
        type_mapping = super()._detailed_type_mapping()
        type_mapping['event_booth'] = 'service'
        return type_mapping


class Product(models.Model):
    _inherit = 'product.product'

    @api.onchange('detailed_type')
    def _onchange_type_event_booth(self):
        if self.detailed_type == 'event_booth':
            self.invoice_policy = 'order'
