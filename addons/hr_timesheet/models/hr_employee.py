from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    has_timesheet = fields.Boolean(
        export_string_translation=False,
        compute="_compute_has_timesheet",
    )

    def _compute_has_timesheet(self):
        if self.ids:
            result = dict(
                self.env.execute_query(
                    SQL(
                        """ SELECT id, EXISTS(
                            SELECT 1 FROM account_analytic_line
                             WHERE project_id IS NOT NULL AND employee_id = e.id
                             LIMIT 1)
                      FROM hr_employee e
                     WHERE id in %s """,
                        tuple(self.ids),
                    )
                )
            )
        else:
            result = {}

        _debug.perf.count("has_timesheet_probed", employees=self, rows=len(result))
        for employee in self:
            employee.has_timesheet = result.get(employee._origin.id, False)

    @api.depends("company_id", "user_id")
    @api.depends_context("allowed_company_ids")
    def _compute_display_name(self):
        super()._compute_display_name()
        allowed_company_ids = self.env.context.get("allowed_company_ids", [])
        if len(allowed_company_ids) <= 1:
            return

        employees_count_per_user = {
            user.id: count
            for user, count in self.env["hr.employee"]
            .sudo()
            ._read_group(
                [
                    ("user_id", "in", self.user_id.ids),
                    ("company_id", "in", allowed_company_ids),
                ],
                ["user_id"],
                ["__count"],
            )
        }
        for employee in self:
            if employees_count_per_user.get(employee.user_id.id, 0) > 1:
                employee.display_name = (
                    f"{employee.display_name} - {employee.company_id.name}"
                )

    def action_unlink_wizard(self):
        wizard = self.env["hr.employee.delete.wizard"].create(
            {
                "employee_ids": self.ids,
            }
        )
        if (
            not self.env.user.has_group("hr_timesheet.group_hr_timesheet_approver")
            and wizard.has_timesheet
            and not wizard.has_active_employee
        ):
            _debug.logic(
                "employee_delete_refused", reason="has_timesheets", employees=self
            )
            raise UserError(_("You cannot delete employees who have timesheets."))

        return {
            "name": _("Confirmation"),
            "view_mode": "form",
            "res_model": "hr.employee.delete.wizard",
            "views": [
                (self.env.ref("hr_timesheet.hr_employee_delete_wizard_form").id, "form")
            ],
            "type": "ir.actions.act_window",
            "res_id": wizard.id,
            "target": "new",
            "context": self.env.context,
        }

    def action_timesheet_from_employee(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "hr_timesheet.timesheet_action_from_employee"
        )
        context = self.env["ir.actions.actions"]._eval_action_context(
            action["context"], active_id=self.id
        )
        context["create"] = context.get("create", True) and self.active
        action["context"] = context
        return action
