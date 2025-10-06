# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    category_id = fields.Many2one(
        comodel_name='product.attribute.category',
        string="eCommerce Category",
        index=True,
        help="Set a category to regroup similar attributes under the same section in the Comparison"
             " page of eCommerce.",
    )
