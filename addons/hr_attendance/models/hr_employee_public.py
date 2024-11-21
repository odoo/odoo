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
    last_attendance_id = fields.Many2one(related='employee_id.last_attendance_id', readonly=True,
        groups="hr_attendance.group_hr_attendance_officer")
    total_overtime = fields.Float(related='employee_id.total_overtime', readonly=True,
        groups="hr_attendance.group_hr_attendance_officer")
    attendance_manager_id = fields.Many2one(related='employee_id.attendance_manager_id',
        groups="hr_attendance.group_hr_attendance_officer")
    last_check_in = fields.Datetime(related='employee_id.last_check_in',
        groups="hr_attendance.group_hr_attendance_officer")
    last_check_out = fields.Datetime(related='employee_id.last_check_out',
        groups="hr_attendance.group_hr_attendance_officer")
