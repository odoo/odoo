# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # TODO: update later once html id generation is fixed
    purchase_add_mode = fields.Selection(
        selection=[
            ('configurator_purchase', "Product Configurator"),
            ('matrix_purchase', "Order Grid Entry"),
        ],
        string="Add purchase mode",
        default='matrix_purchase',
        help="Configurator: choose attribute values to add the matching product variant to the order."
             "\nGrid: add several variants at once from the grid of attribute values")

    def get_single_product_variant(self):
        res = super().get_single_product_variant()
        if self.env.context.get("from_purchase"):
            if self.has_configurable_attributes:
                res['mode'] = self.purchase_add_mode
            else:
                res['mode'] = 'matrix_purchase'
        return res
