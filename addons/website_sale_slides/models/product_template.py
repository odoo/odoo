# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(selection_add=[
        ('course', 'Course'),
    ], ondelete={'course': 'set service'})

    def _detailed_type_mapping(self):
        type_mapping = super(ProductTemplate, self)._detailed_type_mapping()
        type_mapping['course'] = 'service'
        return type_mapping
