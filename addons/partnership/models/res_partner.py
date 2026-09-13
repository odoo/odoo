from odoo import fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    grade_id = fields.Many2one(
        comodel_name="res.partner.grade",
        string="Partner Level",
        group_expand="_read_group_expand_full",
        tracking=True,
    )

    def write(self, vals):
        if vals.get("grade_id"):
            grade = self.env["res.partner.grade"].browse(vals["grade_id"])
            if grade.default_pricelist_id:
                pricelist = vals.get("specific_property_product_pricelist") or vals.get(
                    "property_product_pricelist"
                )
                if pricelist and pricelist != grade.default_pricelist_id.id:
                    raise UserError(
                        self.env._(
                            "You are trying to assign two different pricelists (one directly and one from grade (%(grade_name)s)).",
                            grade_name=grade.name,
                        )
                    )
                vals["specific_property_product_pricelist"] = (
                    grade.default_pricelist_id.id
                )
        return super().write(vals)
