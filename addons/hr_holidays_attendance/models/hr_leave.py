from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


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
            _debug.logic("overtime_check_skipped", leaves=self, fields=list(vals))
            return res
        _debug.pipeline("overtime_check_on_write", leaves=self, fields=list(vals))
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
                _debug.logic(
                    "overtime_insufficient",
                    leave=leave,
                    employee=leave.employee_id,
                    balance=hours[leave.employee_id],
                )
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

    def _force_cancel(self, *args, **kwargs):
        super()._force_cancel(*args, **kwargs)
