# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleProductConfigurator(models.TransientModel):
    _name = 'sale.product.configurator'
    _description = 'Sale Product Configurator'

    product_template_id = fields.Many2one(
        'product.template', string="Product",
        required=True, domain=[('sale_ok', '=', True), '|', ('attribute_line_ids.value_ids', '!=', False), ('optional_product_ids', '!=', False)])
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
