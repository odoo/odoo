# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import api, fields, models
from odoo.addons.resource.models.resource_mixin import timezone_datetime


class HrAttendanceOvertime(models.Model):
    _name = "hr.attendance.overtime"
    _description = "Attendance Overtime"
    _rec_name = 'employee_id'
    _order = 'date desc'

    def _default_employee(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one(
        'hr.employee', string="Employee", default=_default_employee,
        required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='employee_id.company_id')
    attendance_ids = fields.Many2many("hr.attendance", help="Attendance records on the same day as this overtime")
    real_overtime = fields.Boolean(compute="_compute_real_overtime",
                        help="Whether the overtime is to be taken into account or not. Depending on if the employee worked all his hours for that day")
    date = fields.Date(string='Day')
    duration = fields.Float(string='Extra Hours', default=0.0, required=True)
    duration_real = fields.Float(
        string='Extra Hours (Real)', default=0.0,
        help="Extra-hours including the threshold duration")
    adjustment = fields.Boolean(default=False)

    def init(self):
        # Allows only 1 overtime record per employee per day unless it's an adjustment
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS hr_attendance_overtime_unique_employee_per_day
            ON %s (employee_id, date)
            WHERE adjustment is false""" % (self._table))

    # overtime should only be taken into account if employee worked all his regular hours
    @api.depends("attendance_ids")
    def _compute_real_overtime(self):
        for overtime in self:
            start_day = timezone_datetime(datetime.combine(overtime.date, datetime.min.time()))
            end_day = timezone_datetime(datetime.combine(overtime.date, datetime.max.time()))
            day_attendances = self.env["hr.attendance"].search([("check_in", ">=", start_day), ("check_out", "<=", end_day)])
            resource = overtime.employee_id.resource_id
            calendar = resource.calendar_id or resource.company_id.resource_calendar_id
            expected_day_hours = calendar._get_resources_day_total(start_day, end_day, resource)
            overtime.real_overtime = sum(day_attendances.mapped("worked_hours")) - expected_day_hours[resource.id][overtime.date]

    # CRUD METHODS #

    # always update attendance_ids, don't trust incoming values
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            start_day = datetime.combine(vals["date"], datetime.min.time())
            end_day = datetime.combine(vals["date"], datetime.max.time())
            day_attendances = self.env["hr.attendance"].search([("check_in", ">=", start_day), ("check_out", "<=", end_day)])
            vals["attendance_ids"] = day_attendances.ids
        return super().create(vals_list)

    def write(self, vals):
        start_day = datetime.combine(self.date, datetime.min.time())
        end_day = datetime.combine(self.date, datetime.max.time())
        day_attendances = self.env["hr.attendance"].search([("check_in", ">=", start_day), ("check_out", "<=", end_day)])
        vals["attendance_ids"] = day_attendances.ids
        return super().write(vals)
