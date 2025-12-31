# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _get_deductible_employee_overtime(self):
        # return dict {employee: number of hours}
        diff_by_employee = defaultdict(lambda: 0)
        for employee, hours in self.env['hr.attendance.overtime.line'].sudo()._read_group(
            domain=[
                ('compensable_as_leave', '=', True),
                ('employee_id', 'in', self.ids),
                ('status', '=', 'approved'),
            ],
            groupby=['employee_id'],
            aggregates=['manual_duration:sum'],
        ):
            diff_by_employee[employee] += hours
        for employee, hours in self.env['hr.leave']._read_group(
            domain=[
                ('work_entry_type_id.overtime_deductible', '=', True),
                ('work_entry_type_id.requires_allocation', '=', False),
                ('employee_id', 'in', self.ids),
                ('state', 'not in', ['refuse', 'cancel']),
            ],
            groupby=['employee_id'],
            aggregates=['number_of_hours:sum'],
        ):
            diff_by_employee[employee] -= hours
        for employee, hours in self.env['hr.leave.allocation']._read_group(
            domain=[
                ('work_entry_type_id.overtime_deductible', '=', True),
                ('employee_id', 'in', self.ids),
                ('state', 'in', ['confirm', 'validate', 'validate1']),
            ],
            groupby=['employee_id'],
            aggregates=['number_of_hours_display:sum'],
        ):
            diff_by_employee[employee] -= hours
        return diff_by_employee

    def get_attendace_data_by_employee(self, date_start, date_stop):
        attendance_data = super().get_attendace_data_by_employee(date_start, date_stop)
        for employee_id in self.ids:
            attendance_data[employee_id]["unspent_compensable_overtime"] = 0
        unspent_overtime = self._get_deductible_employee_overtime()
        for employee in unspent_overtime:
            attendance_data[employee.id]["unspent_compensable_overtime"] += max(0, unspent_overtime[employee])
        return attendance_data
