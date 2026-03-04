# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    leave_ids = fields.One2many('hr.leave', 'employee_id', groups='hr_holidays.group_hr_holidays_user')
    leave_allocation_ids = fields.One2many('hr.leave.allocation', 'employee_id', groups='hr_holidays.group_hr_holidays_user')
    deductible_overtime = fields.Float(compute='_compute_deductible_overtime', groups='hr_attendance.group_hr_attendance_own_reader')

    @api.depends('attendance_ids.linked_overtime_ids.compensable_as_leave', 'attendance_ids.linked_overtime_ids.status',
                 'attendance_ids.linked_overtime_ids.manual_duration', 'leave_ids.work_entry_type_id.overtime_deductible',
                 'leave_ids.state', 'leave_ids.number_of_hours', 'leave_allocation_ids.work_entry_type_id.overtime_deductible',
                 'leave_allocation_ids.state', 'leave_allocation_ids.number_of_hours_display')
    def _compute_deductible_overtime(self):
        diff_by_employee = defaultdict(lambda: 0)
        for employee, lines in self.env['hr.attendance.overtime.line'].sudo()._read_group(
            domain=[
                ('compensable_as_leave', '=', True),
                ('attendance_id.employee_id', 'in', self.ids),
                ('status', '=', 'approved'),
            ],
            groupby=['attendance_id.employee_id'],
            aggregates=['id:recordset'],
        ):
            for line in lines:
                diff_by_employee[employee] += line.manual_duration * line.leave_compensation_rate
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

        for employee in self:
            employee.deductible_overtime = diff_by_employee[employee]

    def get_attendace_data_by_employee(self, date_start, date_stop):
        attendance_data = super().get_attendace_data_by_employee(date_start, date_stop)
        for employee_id in self.ids:
            attendance_data[employee_id]["unspent_compensable_overtime"] = 0
        for employee in self:
            attendance_data[employee.id]["unspent_compensable_overtime"] += max(0, employee.deductible_overtime)
        return attendance_data
