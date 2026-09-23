# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    parent_id = fields.Many2one(
        "product.attribute.value",
        string="Parent",
        copy=False,
        domain="""[
            ('id', '!=', id),
            ('attribute_id', '=', attribute_id),
            ('parent_id', '=', False),
        ]""",
    )
    child_ids = fields.One2many("product.attribute.value", "parent_id")

    @api.constrains("parent_id")
    def _check_parent_id(self):
        for pav in self:
            if pav.parent_id and (pav.child_ids or pav.parent_id.parent_id):
                raise ValidationError(
                    _("An attribute value cannot be both a parent and a child.")
                )
