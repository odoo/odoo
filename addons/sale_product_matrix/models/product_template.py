# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_add_mode = fields.Selection(
        selection=[
            ('configurator', "Configurator"),
            ('matrix', "Matrix"),
        ],
        string="Variant Selection",
        default='configurator',
        help="Configurator: choose attribute values to add the matching product variant to the order."
             "\nMatrix: add several variants at once from the grid of attribute values")

    def get_single_product_variant(self):
        res = super().get_single_product_variant()
        if self.has_configurable_attributes:
            res['mode'] = self.product_add_mode
        else:
            res['mode'] = 'configurator'
        return res
