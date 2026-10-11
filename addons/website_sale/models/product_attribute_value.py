# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    parent_id = fields.Many2one(
        "product.attribute.value",
        string="Parent",
        domain="""[
            ('id', '!=', id),
            ('attribute_id', '=', attribute_id),
            ('parent_id', '=', False),
        ]""",
    )
    child_ids = fields.One2many("product.attribute.value", "parent_id")
