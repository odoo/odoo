# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    total_margin = fields.Float(compute='_compute_total_margin')

    @api.multi
    def _compute_total_margin(self):
        margin_data = self.env['report.product.margin'].read_group([
            ('product_tmpl_id', 'in', self.ids)
        ], ['total_margin', 'product_tmpl_id'], ['product_tmpl_id'])
        mapped_data = {margin['product_tmpl_id'][0]: margin['total_margin'] for margin in margin_data}
        for product_template in self:
            product_template.total_margin = mapped_data.get(product_template.id)


class Product(models.Model):
    _inherit = "product.product"

    total_margin = fields.Float(compute='_compute_total_margin')

    @api.multi
    def _compute_total_margin(self):
        margin_data = self.env['report.product.margin'].read_group([
            ('product_id', 'in', self.ids)
        ], ['total_margin', 'product_id'], ['product_id'])
        mapped_data = {margin['product_id'][0]: margin['total_margin'] for margin in margin_data}
        for product in self:
            product.total_margin = mapped_data.get(product.id)
