# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    x_attendance_ids = fields.Many2many(
        'hr.attendance',
        'hr_leave_attendance_rel',
        'leave_id',
        'attendance_id',
        string='Attendance Issues',
        domain="[('employee_id', '=', employee_id), "
               "('check_in', '>=', request_date_from), "
               "('check_in', '<=', request_date_to)] + "
               "(['|', ('x_late_minutes', '>', 0), ('x_early_leave_minutes', '>', 0)] "
               "if request_unit_hours else [('x_is_absent', '=', True)])",
        help="Select the attendance records with issues (late, early leave, or absence) "
             "that this time-off request is meant to cover.", )

    x_total_late_minutes = fields.Float(
        string='Total Late Minutes',
        compute='_compute_attendance_summary',
    )

    x_total_early_leave_minutes = fields.Float(
        string='Total Early Leave Minutes',
        compute='_compute_attendance_summary',
    )

    x_total_absent_days = fields.Integer(
        string='Absent Days',
        compute='_compute_attendance_summary',
    )

    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_clear_attendance(self):
        self.x_attendance_ids = [(5, 0, 0)]

    @api.depends('x_attendance_ids')
    def _compute_attendance_summary(self):
        for leave in self:
            leave.x_total_late_minutes = sum(leave.x_attendance_ids.mapped('x_late_minutes'))
            leave.x_total_early_leave_minutes = sum(leave.x_attendance_ids.mapped('x_early_leave_minutes'))
            leave.x_total_absent_days = len(leave.x_attendance_ids.filtered('x_is_absent'))
