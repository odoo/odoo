# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # These are required for manual attendance
    attendance_state = fields.Selection(related='employee_id.attendance_state', readonly=True,
        groups="hr_attendance.group_hr_attendance_officer")
    hours_today = fields.Float(related='employee_id.hours_today', readonly=True,
        groups="hr_attendance.group_hr_attendance_officer")
    hours_last_month = fields.Float(related='employee_id.hours_last_month')
    hours_last_month_overtime = fields.Float(related='employee_id.hours_last_month_overtime')
    last_attendance_id = fields.Many2one(related='employee_id.last_attendance_id', readonly=True,
        groups="hr_attendance.group_hr_attendance_officer")
    total_overtime = fields.Float(related='employee_id.total_overtime', readonly=True)
    attendance_manager_id = fields.Many2one(related='employee_id.attendance_manager_id',
        groups="hr_attendance.group_hr_attendance_officer")
    last_check_in = fields.Datetime(related='employee_id.last_check_in',
        groups="hr_attendance.group_hr_attendance_officer")
    last_check_out = fields.Datetime(related='employee_id.last_check_out',
        groups="hr_attendance.group_hr_attendance_officer")
    display_extra_hours = fields.Boolean(related='company_id.hr_attendance_display_overtime')

    def action_open_last_month_attendances(self):
        self.ensure_one()
        if self.is_user:
            return self.employee_id.action_open_last_month_attendances()
