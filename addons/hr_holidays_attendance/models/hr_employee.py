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
                ('holiday_status_id.overtime_deductible', '=', True),
                ('holiday_status_id.requires_allocation', '=', False),
                ('employee_id', 'in', self.ids),
                ('state', 'not in', ['refuse', 'cancel']),
            ],
            groupby=['employee_id'],
            aggregates=['number_of_hours:sum'],
        ):
            diff_by_employee[employee] -= hours
        for employee, hours in self.env['hr.leave.allocation']._read_group(
            domain=[
                ('holiday_status_id.overtime_deductible', '=', True),
                ('employee_id', 'in', self.ids),
                ('state', 'in', ['confirm', 'validate', 'validate1']),
            ],
            groupby=['employee_id'],
            aggregates=['number_of_hours_display:sum'],
        ):
            diff_by_employee[employee] -= hours
        return diff_by_employee

    def get_overtime_data_by_employee(self):
        """
        Provide a summary of an employee's overtime.
        A compensable overtime is an overtime that can be cumulated to be used
        as time off.
        Extra hours and overtime is used interchangably.
        """
        # Make so that at least all employees are present in return value
        overtime_data = {}
        for employee_id in self.ids:
            overtime_data[employee_id] = {
                "compensable_overtime": 0,
                "not_compensable_overtime": 0,
                "unspent_compensable_overtime": 0,
            }

        unspent_overtime = self._get_deductible_employee_overtime()
        for employee in unspent_overtime:
            overtime_data[employee.id]['unspent_compensable_overtime'] += max(
                0, unspent_overtime[employee]
            )

        all_overtimes = self.env['hr.attendance.overtime.line']._read_group(
            domain=[
                ('employee_id', 'in', self.ids),
            ],
            groupby=["employee_id", "compensable_as_leave"],
            aggregates=["duration:sum"],
        )
        for employee, is_compensable, amount in all_overtimes:
            overtime_type = (
                'compensable_overtime'
                if is_compensable
                else 'not_compensable_overtime'
            )
            overtime_data[employee.id][overtime_type] += amount

        return overtime_data
