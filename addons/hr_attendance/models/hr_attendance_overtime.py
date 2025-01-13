# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrAttendanceOvertime(models.Model):
    _name = 'hr.attendance.overtime'
    _description = "Attendance Overtime"
    _rec_name = 'employee_id'
    _order = 'date desc'

    def _default_employee(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one(
        'hr.employee', string="Employee", default=_default_employee,
        required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='employee_id.company_id')

    date = fields.Date(string='Day', index=True, required=True)
    duration = fields.Float(string='Extra Hours', default=0.0, required=True)
    duration_real = fields.Float(
        string='Extra Hours (Real)', default=0.0,
        help="Extra-hours including the threshold duration")
    adjustment = fields.Boolean(default=False)

    # Allows only 1 overtime record per employee per day unless it's an adjustment
    _unique_employee_per_day = models.UniqueIndex("(employee_id, date) WHERE adjustment IS NOT TRUE")
