# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    scientific_name = fields.Many2one('aumet.scientific_name', string='Scientific Name', required=False)
    marketplace_product = fields.Many2one('aumet.marketplace_product', string='Marketplace Product', required=False)
    is_marketplace_item = fields.Boolean(string="Is from marketplace")
    payment_method = fields.Many2one("aumet.payment_method", string="payment method")

    price_unit = fields.Float(
        'Unit Price', compute='_compute_standard_price', store=False)

    def _compute_standard_price(self):
        try:
            self.price_unit = 200
            self.standard_price = self.marketplace_product.unit_price
        except Exception as exc1:
            print(exc1)

        self.list_price = 200
        self.standard_price = 200

    @api.depends('marketplace_reference')
    def compute_referenced(self):
        self.marketplace_referenced = True if self.marketplace_product else False
