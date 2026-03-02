# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models
from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    def _get_accrual_plan_level_work_entry_prorata(self, level, start_period, start_date, end_period, end_date):
        """For ``worked_hours`` levels, return the hours of the validated attendances of the
        employee between ``start_date`` and ``end_date``.

        The attendance spans are united and clipped to the period; breaks are not deducted.

        :rtype: float
        """
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

<<<<<<< 7349287698e25ca2bddddb94dcd72a2bb3f1b77b
        attendance_intervals = []
        for att in attendances:
            attendance_intervals.append((att.check_in, att.check_out, att))
||||||| fb11a4e4d14c90eddcac5d9dfdc214ca1be21d0d
        total_worked_hours = 0.0
        for attendance in attendances:
            total_worked_hours += attendance._get_worked_hours_in_range(start_dt, end_dt)
=======
        total_worked_hours = 0.0
        for attendance in attendances:
            worked_hours = attendance._get_worked_hours_in_range(start_dt, end_dt)
            # Only the approved extra hours count: the ones still to approve or refused are left out
            approved_overtime = attendance.validated_overtime_hours if attendance.overtime_status == 'approved' else 0.0
            unapproved_overtime = max(0.0, attendance.overtime_hours - approved_overtime)
            if worked_hours and unapproved_overtime:
                # Prorated to the part of the attendance in the period (an attendance across midnight)
                attendance_hours = attendance.worked_hours or attendance._get_worked_hours_in_range(attendance.check_in, attendance.check_out)
                if attendance_hours:
                    unapproved_overtime *= min(1.0, worked_hours / attendance_hours)
                worked_hours = max(0.0, worked_hours - unapproved_overtime)
            total_worked_hours += worked_hours
>>>>>>> b610b25aa82974f3bc080f0205272897753a2599

        worked_interval = Intervals(attendance_intervals) & Intervals([(start_dt, end_dt, self.env['hr.attendance'])])
        return sum_intervals(worked_interval)
