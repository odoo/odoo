# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrLeaveAccrualLevel(models.Model):
    _inherit = "hr.leave.accrual.level"

    frequency = fields.Selection(
        selection_add=[('worked_hours', 'Per Hour Worked')],
        ondelete={'worked_hours': 'cascade'},
        compute='_compute_frequency',
        store=True,
        readonly=False,
    )

    @api.constrains('frequency')
    def _check_worked_hours(self):
        for level in self:
            if level.frequency == 'worked_hours' and level.accrued_gain_time == 'start':
                raise ValidationError(self.env._("You can't base accrued time on hours worked, because time is accrued at the start of the period."))

    @api.depends('accrued_gain_time')
    def _compute_frequency(self):
        for level in self:
            if level.accrued_gain_time == 'start' and level.frequency == 'worked_hours':
                level.frequency = 'hourly'

    @api.depends('frequency', 'added_value')
    def _compute_yearly_gain(self):
        super()._compute_yearly_gain()
        company_calendar = self.env.company.resource_calendar_id
        hours_per_week = company_calendar.hours_per_week
        for level in self:
            if level.frequency == 'worked_hours':
                level.yearly_gain = level.added_value * 52 * hours_per_week

    def _get_hourly_frequencies(self):
        return super()._get_hourly_frequencies() + ["worked_hours"]
