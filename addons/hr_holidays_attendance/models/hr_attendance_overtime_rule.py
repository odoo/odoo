
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrAttendanceOvertimeRule(models.Model):
    _name = 'hr.attendance.overtime.rule'
    _inherit = 'hr.attendance.overtime.rule'

    compensable_as_leave = fields.Boolean("Give back as time off", default=False)
    timing_type = fields.Selection(selection_add=[
        ('leave', "When employee is off"),
        ('public_leave', "On a Public holiday"),
    ])

    def _extra_overtime_vals(self):
        if not self:
            return {
                **super()._extra_overtime_vals(),
                'compensable_as_leave': False,
            }

        res = super()._extra_overtime_vals()
        res['compensable_as_leave'] = any(self.mapped('compensable_as_leave'))
        if self.ruleset_id.rate_combination_mode == 'sum' and any(self.mapped('paid')):
            combined_rate = 1.0
            combined_rate += sum(r.amount_rate - 1.0 for r in self.filtered(
                lambda r: r.paid and not r.compensable_as_leave
            ))
            combined_rate += sum(r.amount_rate for r in self.filtered(
                lambda r: r.paid and r.compensable_as_leave
            ))
            res['amount_rate'] = combined_rate
        return res

    def _get_timing_type_overtime_by_attendance_by_employee(self, employees, intervals_by_timing_type, attendances_intervals_by_employee):
        OvertimeRule = self.env['hr.attendance.overtime.rule']
        overtime_by_attendance_by_employee = super()._get_timing_type_overtime_by_attendance_by_employee(
            employees, intervals_by_timing_type, attendances_intervals_by_employee)

        if leave_rules := self.filtered(lambda rule: rule.timing_type == 'leave'):
            self._update_overtime_by_attendance_by_employee(
                overtime_by_attendance_by_employee, employees, leave_rules, intervals_by_timing_type['leave'], attendances_intervals_by_employee)

        # Same code as for 'work_days' and 'non_work_days'
        for rule in self.filtered(lambda rule: rule.timing_type == 'public_leave'):
            days_by_employee = {
                employee: {start_date.date() for start_date, _end_date, _rule in intervals_by_timing_type['public_leave'][employee]}
                    for employee in employees
            }
            timing_intervals_by_employee = OvertimeRule._build_day_rule_intervals_by_employee(employees, rule, days_by_employee)
            OvertimeRule._update_overtime_by_attendance_by_employee(
                overtime_by_attendance_by_employee, employees, rule, timing_intervals_by_employee, attendances_intervals_by_employee)

        return overtime_by_attendance_by_employee
