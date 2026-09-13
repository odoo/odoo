from odoo import api, fields, models

from ..tools import debug_log as dbg


class MixinHrManagerDepartmentReport(models.AbstractModel):
    _name = "mixin.hr.manager.department.report"
    _description = "Hr Manager Department Report"
    _auto = False

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        readonly=True,
    )
    has_department_manager_access = fields.Boolean(
        compute="_compute_has_department_manager_access",
        search="_search_has_department_manager_access",
    )

    def _get_managed_department_ids(self):
        managed = tuple(
            self.env["hr.department"]._search(
                [("manager_id", "in", self.env.user.employee_ids.ids)]
            )
        )
        dbg.logic.debug(
            "%s: user %s (employees %s) manages departments %s",
            self._name,
            self.env.uid,
            self.env.user.employee_ids.ids,
            managed,
        )
        return managed

    def _search_has_department_manager_access(self, operator, value):
        if operator != "in":
            return NotImplemented
        return [
            "|",
            ("employee_id.user_id", "=", self.env.user.id),
            (
                "employee_id.department_id",
                "child_of",
                self._get_managed_department_ids(),
            ),
        ]

    @dbg.timed
    @api.depends_context("uid")
    @api.depends("employee_id")
    def _compute_has_department_manager_access(self):
        employees = self.env["hr.employee"].search(
            [
                "|",
                ("user_id", "=", self.env.user.id),
                (
                    "department_id",
                    "child_of",
                    self._get_managed_department_ids(),
                ),
            ]
        )
        for report in self:
            report.has_department_manager_access = report.employee_id in employees
