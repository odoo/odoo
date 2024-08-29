# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import product

from odoo import fields, models


class ProductAttribute(models.Model, product.ProductAttribute):
    _order = 'category_id, sequence, id'

    category_id = fields.Many2one(
        comodel_name='product.attribute.category',
        string="eCommerce Category",
        index=True,
        help="Set a category to regroup similar attributes under the same section in the Comparison"
             " page of eCommerce.",
    )
