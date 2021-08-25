# -*- coding: utf-8 -*-

from odoo import api, fields, models

import json


class ProductTemplate(models.Model):
    _inherit = "product.template"

    qr_code = fields.Char(
        ' QR  code', copy=False,
        help="International Article Number used for product identification.")
    default_code = fields.Char(
        'Code', compute='_compute_default_code',
        inverse='_set_default_code', store=True)
    granular_unit = fields.Char('Granular Unit')
    manufacturer = fields.Char('Manufacture')

    @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    def _compute_default_code(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.default_code = template.product_variant_ids.default_code
        for template in (self - unique_variants):
            template.default_code = False


