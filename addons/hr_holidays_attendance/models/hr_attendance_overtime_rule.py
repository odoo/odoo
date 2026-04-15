
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields
from odoo.tools.intervals import Intervals


class HrAttendanceOvertimeRule(models.Model):
    _name = 'hr.attendance.overtime.rule'
    _inherit = 'hr.attendance.overtime.rule'

    compensable_as_leave = fields.Boolean("Give back as time off", default=False)
    leave_compensation_rate = fields.Float(default=1.0)
    timing_type = fields.Selection(selection_add=[
        ('leave', "When employee is off"),
        ('public_leave', "On a Public holiday"),
    ])

    def _get_rules_intervals_by_timing_type(self, min_check_in, max_check_out, employees, schedules_intervals_by_employee):
        intervals_by_timing_type = super()._get_rules_intervals_by_timing_type(
            min_check_in, max_check_out, employees, schedules_intervals_by_employee,
        )
        timing_type_set = set(self.grouped('timing_type').keys())
        if 'leave' in timing_type_set:
            intervals_by_timing_type['leave'] = schedules_intervals_by_employee['leave']
        if 'public_leave' in timing_type_set:
            public_leave_intervals = defaultdict(Intervals)
            for employee in employees:
                public_leave_intervals[employee] = self._generate_days_intervals(
                    schedules_intervals_by_employee['public_leave'][employee]
                )
            intervals_by_timing_type['public_leave'] = public_leave_intervals
        return intervals_by_timing_type

    def _get_overtime_by_employee_by_attendance(self, employees, intervals_by_timing_type, attendances_intervals_by_employee):
        leave_rules = self.filtered(lambda r: r.timing_type == 'leave')
        overtime_by_employee_by_attendance = super(HrAttendanceOvertimeRule, self - leave_rules)._get_overtime_by_employee_by_attendance(
            employees,
            intervals_by_timing_type,
            attendances_intervals_by_employee,
        )
        if leave_rules:
            leave_rules._map_timing_type_overtime_by_employee_by_attendance(
                employees,
                intervals_by_timing_type['leave'],
                attendances_intervals_by_employee,
                overtime_by_employee_by_attendance,
            )
        return overtime_by_employee_by_attendance

    def _extra_overtime_vals(self):

        cal_rules = self.filtered('compensable_as_leave')

        total_leave_compensation_rate = 0.0
        if cal_rules:
            if self.ruleset_id.rate_combination_mode == 'sum':
                total_leave_compensation_rate = sum((r.leave_compensation_rate - 1.0 for r in cal_rules), start=1.0)
            elif self.ruleset_id.rate_combination_mode == 'max':
                total_leave_compensation_rate = max(r.leave_compensation_rate for r in cal_rules)

        return {
            **super()._extra_overtime_vals(),
            'compensable_as_leave': any(self.mapped('compensable_as_leave')),
            'leave_compensation_rate': total_leave_compensation_rate,
        }
