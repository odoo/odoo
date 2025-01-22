# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class HrLeaveAccrualLevel(models.Model):
    _inherit = "hr.leave.accrual.level"

    frequency = fields.Selection(
        selection_add=[('worked_hours', 'Per Hours Worked')],
        ondelete={ 'worked_hours': 'cascade' },
        compute='_compute_frequency',
        store=True,
        readonly=False,
    )

    _check_dates = models.Constraint(
        "CHECK(accrued_gain_time <> 'start' OR frequency <> 'worked_hours')",
        "You can't base accrued time on hours worked, because time is accrued at the start of the period.",
    )

    def _get_next_date(self, last_call):
        if self.frequency == 'worked_hours':
            return last_call + relativedelta(days=1)
        return super()._get_next_date(last_call)

    @api.depends('accrued_gain_time')
    def _compute_frequency(self):
        for level in self:
            if level.accrued_gain_time == 'start' and level.frequency == 'worked_hours':
                level.frequency = 'hourly'
