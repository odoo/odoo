# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(selection_add=[
        ('course', 'Course'),
    ], ondelete={'course': 'set service'})

    def _detailed_type_mapping(self):
        type_mapping = super(ProductTemplate, self)._detailed_type_mapping()
        type_mapping['course'] = 'service'
        return type_mapping

    @api.model
    def _get_product_types_allow_zero_price(self):
        return super()._get_product_types_allow_zero_price() + ["course"]
