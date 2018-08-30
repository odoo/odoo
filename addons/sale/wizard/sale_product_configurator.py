# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleProductConfigurator(models.TransientModel):
    _name = 'sale.product.configurator'

    product_template_id = fields.Many2one(
        'product.template', string="Product",
        required=True, domain=['|', ('attribute_line_ids', '!=', False), ('optional_product_ids', '!=', False)])
