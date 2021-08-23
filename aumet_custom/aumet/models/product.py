# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    scientific_name = fields.Many2one('aumet.scientific_name', string='Scientific Name', required=False)
    marketplace_product = fields.Many2one('aumet.marketplace_product', string='Marketplace Product', required=False)
    is_marketplace_item = fields.Boolean(string="Is from marketplace")

    @api.depends('marketplace_reference')
    def compute_referenced(self):
        self.marketplace_referenced = True if self.marketplace_product else False
