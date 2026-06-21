# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    def _get_accrual_plan_level_work_entry_prorata(self, level, start_period, start_date, end_period, end_date):
        self.ensure_one()
        if level.frequency != 'worked_hours':
            return super()._get_accrual_plan_level_work_entry_prorata(level, start_period, start_date, end_period, end_date)
        datetime_min_time = datetime.min.time()
        start_dt = datetime.combine(start_date, datetime_min_time)
        end_dt = datetime.combine(end_date, datetime_min_time)

        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '<', end_dt),
            ('check_out', '>', start_dt),
            ('state', '=', 'validated'),
        ])

        total_worked_hours = 0.0
        for attendance in attendances:
            total_worked_hours += attendance._get_worked_hours_in_range(start_dt, end_dt)

        return total_worked_hours
