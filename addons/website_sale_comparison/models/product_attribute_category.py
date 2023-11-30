# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductAttributeCategory(models.Model):
    _name = "product.attribute.category"
    _description = "Product Attribute Category"
    _order = 'sequence, id'

    name = fields.Char("Category Name", required=True, translate=True)
    sequence = fields.Integer("Sequence", default=10, index=True)

    attribute_ids = fields.One2many('product.attribute', 'category_id', string="Related Attributes", domain="[('category_id', '=', False)]")
