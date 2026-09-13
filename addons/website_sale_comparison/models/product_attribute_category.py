from odoo import fields, models


class ProductAttributeCategory(models.Model):
    _name = "product.attribute.category"
    _description = "Product Attribute Category"
    _order = "sequence, id"

    name = fields.Char(
        string="Category Name",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(
        default=10,
        index=True,
    )

    attribute_ids = fields.One2many(
        comodel_name="product.attribute",
        inverse_name="category_id",
        string="Related Attributes",
        domain="[('category_id', '=', False)]",
    )
