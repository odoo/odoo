from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    holiday_id = fields.Many2one(
        comodel_name="hr.leave",
        string="Time Off Request",
        export_string_translation=False,
        index="btree_not_null",
        copy=False,
    )
    global_leave_id = fields.Many2one(
        comodel_name="resource.schedule.exception",
        string="Global Time Off",
        export_string_translation=False,
        index="btree_not_null",
        ondelete="cascade",
    )
    task_id = fields.Many2one(
        domain="[('allow_timesheets', '=', True), ('project_id', '=?', project_id), ('has_template_ancestor', '=', False), ('is_timeoff_task', '=', False)]"
    )

    _timeoff_timesheet_idx = models.Index(
        "(task_id) WHERE (global_leave_id IS NOT NULL OR holiday_id IS NOT NULL) AND project_id IS NOT NULL"
    )

    def _get_redirect_action(self):
        leave_form_view_id = self.env.ref("hr_holidays.hr_leave_view_form").id
        action_data = {
            "name": _("Time Off"),
            "type": "ir.actions.act_window",
            "res_model": "hr.leave",
            "views": [
                (self.env.ref("hr_holidays.hr_leave_view_tree_my").id, "list"),
                (leave_form_view_id, "form"),
            ],
            "domain": [("id", "in", self.holiday_id.ids)],
        }
        if len(self.holiday_id) == 1:
            action_data["views"] = [(leave_form_view_id, "form")]
            action_data["res_id"] = self.holiday_id.id
        return action_data

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_leave(self):
        if any(line.global_leave_id for line in self):
            _debug.logic(
                "timesheet_unlink_refused",
                reason="linked_to_global_time_off",
                lines=self,
            )
            raise UserError(
                _("You cannot delete timesheets that are linked to global time off.")
            )
        if any(line.holiday_id for line in self):
            error_message = _(
                "You cannot delete timesheets that are linked to time off requests. Please cancel your time off request from the Time Off application instead."
            )
            if (
                not self.env.user.has_group("hr_holidays.group_hr_holidays_user")
                and self.env.user not in self.holiday_id.sudo().user_id
            ):
                _debug.logic(
                    "timesheet_unlink_refused",
                    reason="linked_to_leave_and_not_the_owner",
                    lines=self,
                    leaves=self.holiday_id,
                    user=self.env.user,
                )
                raise UserError(error_message)
            action = self._get_redirect_action()
            _debug.logic(
                "timesheet_unlink_redirected",
                reason="linked_to_leave",
                lines=self,
                leaves=self.holiday_id,
                user=self.env.user,
            )
            raise RedirectWarning(error_message, action, _("View Time Off"))

    def _check_can_write(self, values):
        if not self.env.su and self.holiday_id:
            _debug.logic(
                "timesheet_write_refused",
                reason="linked_to_leave",
                lines=self,
                leaves=self.holiday_id,
                fields=len(values),
            )
            raise UserError(
                _(
                    "You cannot modify timesheets that are linked to time off requests. Please use the Time Off application to modify your time off requests instead."
                )
            )
        return super()._check_can_write(values)

    def _check_can_create(self):
        if not self.env.su and any(task.is_timeoff_task for task in self.task_id):
            _debug.logic(
                "timesheet_create_refused",
                reason="task_is_a_time_off_task",
                tasks=self.task_id,
            )
            raise UserError(
                _(
                    "You cannot create timesheets for a task that is linked to a time off type. Please use the Time Off application to request new time off instead."
                )
            )
        return super()._check_can_create()

    def _get_domain_favorite_project_id(self, employee_id=False):
        return Domain.AND(
            [
                super()._get_domain_favorite_project_id(employee_id),
                Domain("holiday_id", "=", False),
                Domain("global_leave_id", "=", False),
            ]
        )
