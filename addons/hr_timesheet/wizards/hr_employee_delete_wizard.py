from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployeeDeleteWizard(models.TransientModel):
    _name = "hr.employee.delete.wizard"
    _description = "Employee Delete Wizard"

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
        export_string_translation=False,
        context={"active_test": False},
    )
    has_active_employee = fields.Boolean(
        export_string_translation=False,
        compute="_compute_has_active_employee",
    )
    has_timesheet = fields.Boolean(
        export_string_translation=False,
        compute="_compute_has_timesheet",
        compute_sudo=True,
    )

    @api.depends("employee_ids")
    def _compute_has_timesheet(self):
        timesheet_read_group = self.env["account.analytic.line"]._read_group(
            [("employee_id", "in", self.employee_ids.ids)],
            ["employee_id"],
        )
        timesheet_employee_map = {employee.id for [employee] in timesheet_read_group}
        for wizard in self:
            wizard.has_timesheet = timesheet_employee_map & set(wizard.employee_ids.ids)

    @api.depends("employee_ids")
    def _compute_has_active_employee(self):
        unarchived_employees = self.env["hr.employee"].search(
            [("id", "=", self.employee_ids.ids)]
        )
        for wizard in self:
            wizard.has_active_employee = any(
                emp in wizard.employee_ids for emp in unarchived_employees
            )

    def action_archive(self):
        self.check_singleton()
        _debug.pipeline("employee_delete_to_departure", employees=self.employee_ids)
        return {
            "name": _("Employee Termination"),
            "type": "ir.actions.act_window",
            "res_model": "hr.departure.wizard",
            "views": [[False, "form"]],
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_ids": self.employee_ids.ids,
                "employee_termination": True,
            },
        }

    def action_confirm_delete(self):
        self.check_singleton()
        _debug.lifecycle("employees_deleted", employees=self.employee_ids)
        self.employee_ids.unlink()
        return self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "hr.open_view_employee_list_my"
        )

    def action_view_timesheets(self):
        self.check_singleton()
        employees = self.with_context(active_test=False).employee_ids
        action = {
            "name": _("Employees' Timesheets"),
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.line",
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "domain": [
                ("employee_id", "in", employees.ids),
                ("project_id", "!=", False),
            ],
        }
        if len(employees) == 1:
            action["name"] = _("Timesheets of %(name)s", name=employees.name)
        return action
