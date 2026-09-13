from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrLeaveAccrualLevel(models.Model):
    _inherit = "hr.leave.accrual.level"

    accrual_basis = fields.Selection(
        selection_add=[("worked_hour", "Per Hour Worked")],
        compute="_compute_accrual_basis",
        store=True,
        readonly=False,
        ondelete={"worked_hour": "set default"},
    )
    frequency = fields.Selection(selection_add=[("worked_hours", "Per Hour Worked")])

    @api.constrains("accrual_basis")
    def _check_worked_hours(self):
        for level in self:
            if (
                level.accrual_basis == "worked_hour"
                and level.accrued_gain_time == "start"
            ):
                raise ValidationError(
                    self.env._(
                        "You can't base accrued time on hours worked, because time is accrued at the start of the period."
                    )
                )

    @api.depends("accrued_gain_time")
    def _compute_accrual_basis(self):
        for level in self:
            if (
                level.accrued_gain_time == "start"
                and level.accrual_basis == "worked_hour"
            ):
                level.accrual_basis = "hour"

    def _get_frequency_cadences(self):
        return {
            **super()._get_frequency_cadences(),
            "worked_hours": ("day", False, "worked_hour"),
        }

    def _get_hourly_bases(self):
        return super()._get_hourly_bases() + ["worked_hour"]
