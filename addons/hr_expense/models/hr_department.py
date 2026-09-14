from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrDepartment(models.Model):
    _inherit = "hr.department"

    expenses_to_approve_count = fields.Integer(
        string="Expenses to Approve",
        compute="_compute_expenses_to_approve_count",
    )

    def _compute_expenses_to_approve_count(self):
        expense_data = self.env["hr.expense"]._read_group(
            [("department_id", "in", self.ids), ("state", "=", "submitted")],
            ["department_id"],
            ["__count"],
        )
        result = {department.id: count for department, count in expense_data}
        _debug.perf.count(
            "departments_to_approve_counted", departments=self, groups=len(result)
        )
        for department in self:
            department.expenses_to_approve_count = result.get(department.id, 0)
