# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

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

        unspent_overtime = self.env[
            'hr.leave'
        ]._get_deductible_employee_overtime(self)
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
