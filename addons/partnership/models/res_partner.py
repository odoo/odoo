from odoo import fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


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
                    _debug.logic(
                        "pricelist_conflict",
                        partners=self,
                        grade=grade,
                        requested=pricelist,
                    )
                    raise UserError(
                        self.env._(
                            "You are trying to assign two different pricelists (one directly and one from grade (%(grade_name)s)).",
                            grade_name=grade.name,
                        )
                    )
                _debug.lifecycle(
                    "pricelist_from_grade",
                    partners=self,
                    grade=grade,
                    pricelist=grade.default_pricelist_id,
                )
                vals["specific_property_product_pricelist"] = (
                    grade.default_pricelist_id.id
                )
        return super().write(vals)
