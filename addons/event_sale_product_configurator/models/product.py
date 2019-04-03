# -*- coding: utf-8 -*-

from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('event_ok')
    def _onchange_event_ok(self):
        super(ProductTemplate, self)._onchange_event_ok()
        if self.event_ok:
            self.optional_product_ids = self.env['product.template']


class Product(models.Model):
    _inherit = 'product.product'

    @api.onchange('event_ok')
    def _onchange_event_ok(self):
        """ Redirection, inheritance mechanism hides the method on the model """
        super(Product, self)._onchange_event_ok()
        if self.event_ok:
            self.optional_product_ids = self.env['product.template']
