from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    assigned_grade_id = fields.Many2one(
        comodel_name="res.partner.grade",
        compute="_compute_assigned_grade_id",
    )

    @api.constrains("line_ids")
    def _constraint_unique_assigned_grade(self):
        for so in self:
            if len(set(so.line_ids.mapped("product_id.grade_id"))) > 1:
                _debug.logic(
                    "grade_conflict", order=so, grades=so.line_ids.product_id.grade_id
                )
                raise ValidationError(
                    so.env._(
                        "You cannot confirm Sale Order %(sale_order_name)s because there are products"
                        " assigning different grades.",
                        sale_order_name=so.name,
                    )
                )

    @api.depends("line_ids.product_id")
    def _compute_assigned_grade_id(self):
        for so in self:
            partnership_lines = so.line_ids.filtered(
                lambda l: l.service_tracking == "partnership"
            )
            so.assigned_grade_id = partnership_lines.mapped("product_id.grade_id")[:1]
            if _debug.logic.enabled and partnership_lines:
                _debug.logic(
                    "partnership_grade_assigned",
                    order=so,
                    lines=partnership_lines,
                    grade=so.assigned_grade_id,
                )

    def action_confirm(self):
        res = super().action_confirm()
        self._add_partnership()
        return res

    def _add_partnership(self):
        for so in self:
            if not so.assigned_grade_id:
                continue
            _debug.lifecycle(
                "partner_grade_set",
                order=so,
                partner=so.partner_id.commercial_partner_id,
                grade=so.assigned_grade_id,
            )
            so.partner_id.commercial_partner_id.grade_id = so.assigned_grade_id
