# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    parent_id = fields.Many2one(
        string="Parent",
        help="Set a parent to group this value under it in the eCommerce filters.",
        comodel_name="product.attribute.value",
        domain="""[
            ('id', '!=', id),
            ('attribute_id', '=', attribute_id),
            ('parent_id', '=', False),
        ]""",
        copy=False,
        index=True,
    )
    child_ids = fields.One2many(
        string="Children",
        comodel_name="product.attribute.value",
        inverse_name="parent_id",
    )

    @api.constrains("parent_id")
    def _check_parent_id(self):
        for pav in self:
            if pav.parent_id and (
                pav.child_ids
                or pav.parent_id.parent_id
                or pav.attribute_id != pav.parent_id.attribute_id
            ):
                raise ValidationError(
                    self.env._(
                        "An attribute value cannot be both a parent and a child, and must belong to the same attribute."
                    )
                )

    def write(self, vals):
        if vals.get("active") is False:
            self.mapped("child_ids").write({
                "parent_id": False,
            })
        return super().write(vals)
