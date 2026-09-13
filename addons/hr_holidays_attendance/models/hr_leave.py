from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrLeave(models.Model):
    _inherit = "hr.leave"

    employee_overtime = fields.Float(
        compute="_compute_employee_overtime",
        groups="base.group_user",
    )
    overtime_deductible = fields.Boolean(compute="_compute_overtime_deductible")

    @api.depends("holiday_status_id")
    def _compute_overtime_deductible(self):
        for leave in self:
            leave.overtime_deductible = (
                leave.holiday_status_id.overtime_deductible
                and not leave.holiday_status_id.requires_allocation
            )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self._check_overtime_deductible(res)
        return res

    OVERTIME_TRIGGER_FIELDS = frozenset(
        {
            "date_from",
            "date_to",
            "employee_id",
            "holiday_status_id",
            "number_of_days",
            "request_date_from",
            "request_date_to",
            "state",
        }
    )

    def write(self, vals):
        res = super().write(vals)
        if self.OVERTIME_TRIGGER_FIELDS.isdisjoint(vals):
            return res
        self._check_overtime_deductible(self)
        return res

    @api.model
    def _get_deductible_employee_overtime(self, employees):
        return employees._get_deductible_employee_overtime()

    @api.depends("number_of_hours", "employee_id", "holiday_status_id")
    def _compute_employee_overtime(self):
        diff_by_employee = self.employee_id._get_deductible_employee_overtime()
        for leave in self:
            leave.employee_overtime = diff_by_employee[leave.employee_id]

    def _check_overtime_deductible(self, leaves):
        hours = leaves.employee_id._get_deductible_employee_overtime()
        for leave in leaves.filtered("overtime_deductible"):
            if hours[leave.employee_id] < 0:
                if leave.employee_id.user_id == self.env.user:
                    raise ValidationError(
                        _("You do not have enough extra hours to request this leave")
                    )
                raise ValidationError(
                    _(
                        "The employee does not have enough extra hours to request this leave."
                    )
                )

    def action_approve(self, check_state=True):
        res = super().action_approve(check_state)
        self._check_overtime_deductible(self)
        return res

    def action_refuse(self):
        return super().action_refuse()

    def _apply_leave_request(self):
        super()._apply_leave_request()
        self._update_leaves_overtime()

    def _remove_resource_leave(self):
        res = super()._remove_resource_leave()
        self._update_leaves_overtime()
        return res

    def _update_leaves_overtime(self):
        Attendance = self.env["hr.attendance"]
        dates = [
            Attendance._get_day_start_and_day(leave.employee_id, leave.date_from)[1]
            for leave in self.filtered(lambda leave: leave.state == "confirmed")
        ]
        if dates:
            Attendance.search(
                [
                    ("date", ">=", min(dates)),
                    ("date", "<=", max(dates)),
                    ("employee_id", "in", self.employee_id.ids),
                ]
            )._update_overtime()

    def _force_cancel(self, *args, **kwargs):
        super()._force_cancel(*args, **kwargs)
