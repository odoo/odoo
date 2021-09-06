# -*- coding: utf-8 -*-

from odoo import api, fields, models

import json


class ProductTemplate(models.Model):
    _inherit = "product.template"


    type = fields.Selection([
        ('product', 'Storable Product'),
        ('consu', 'Consumable'),
        ('service', 'Service')], string='Product Type', default='product', required=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')
    available_in_pos = fields.Boolean(string='Available in POS', help='Check if you want this product to appear in the Point of Sale.', default=True)
    qr_code = fields.Char(
        ' QR  code', copy=False,
        help="International Article Number used for product identification.")
    default_code = fields.Char(
        'Code', compute='_compute_default_code',
        inverse='_set_default_code', store=True)
    granular_unit = fields.Char('Granular Unit')
    manufacturer = fields.Char('Manufacture')


    def _set_default_code(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.default_code = template.default_code

    @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    def _compute_default_code(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.default_code = template.product_variant_ids.default_code
        for template in (self - unique_variants):
            template.default_code = False






class ProductProduct(models.Model):
    _inherit = "product.product"

    qr_code = fields.Char(
        ' QR  code', copy=False,
        help="International Article Number used for product identification.")
    default_code = fields.Char(
        'Code', compute='_compute_default_code',
        inverse='_set_default_code', store=True)
    granular_unit = fields.Char('Granular Unit')
    manufacturer = fields.Char('Manufacture')


    def _set_default_code(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.default_code = template.default_code

    @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    def _compute_default_code(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.default_code = template.product_variant_ids.default_code
        for template in (self - unique_variants):
            template.default_code = False


