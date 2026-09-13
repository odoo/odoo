from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    category_id = fields.Many2one(
        comodel_name="product.attribute.category",
        string="eCommerce Category",
        help="Set a category to regroup similar attributes under the same section in the Comparison"
        " page of eCommerce.",
        index=True,
    )
