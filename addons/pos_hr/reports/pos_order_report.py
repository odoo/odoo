from odoo import fields, models


class ReportPosOrder(models.Model):
    _inherit = "report.pos.order"

    _depends = {"pos.order": ["employee_id"]}

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        readonly=True,
    )

    def _get_fields_select(self) -> dict:
        return {
            **super()._get_fields_select(),
            "employee_id": "s.employee_id",
        }
