# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleProductConfigurator(models.TransientModel):
    _name = 'sale.product.configurator'
    _description = 'Sale Product Configurator'

    product_template_id = fields.Many2one(
        'product.template', string="Product",
        required=True, domain=[('sale_ok', '=', True), ('attribute_line_ids.value_ids', '!=', False)])
    quantity = fields.Integer('Quantity')
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    product_template_attribute_value_ids = fields.Many2many(
        'product.template.attribute.value', 'product_configurator_template_attribute_value_rel', string='Attribute Values', readonly=True)
    product_custom_attribute_value_ids = fields.Many2many(
        'product.attribute.custom.value', 'product_configurator_custom_attribute_value_rel', string="Custom Values")
    product_no_variant_attribute_value_ids = fields.Many2many(
        'product.template.attribute.value', 'product_configurator_no_variant_attribute_value_rel', string="Extra Values")
