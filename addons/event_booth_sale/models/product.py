# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_event_booth = fields.Boolean(string='Is an Event Booth')

    @api.onchange('is_event_booth')
    def _onchange_is_event_booth(self):
        if self.is_event_booth:
            self.type = 'service'
            self.invoice_policy = 'order'


class Product(models.Model):
    _inherit = 'product.product'

    @api.onchange('is_event_booth')
    def _onchange_is_event_booth(self):
        if self.is_event_booth:
            self.type = 'service'
            self.invoice_policy = 'order'
