# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_add_mode = fields.Selection(
        selection=[
            ('configurator', "Product Configurator"),
            ('matrix', "Order Grid Entry"),
        ],
        string="Add product mode",
        default='configurator',
        help="Configurator: choose attribute values to add the matching product variant to the order."
             "\nGrid: add several variants at once from the grid of attribute values")

    def _get_dialog_type(self):
        if self.product_add_mode == 'matrix':
            return 'matrix'
        return super()._get_dialog_type()
