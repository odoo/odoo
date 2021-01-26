# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, tools


class HRAttendanceReport(models.Model):
    _name = "hr.attendance.report"
    _description = "Attendance Statistics"
    _auto = False

    department_id = fields.Many2one('hr.department', string="Department", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    check_in = fields.Datetime("Check In", readonly=True)
    worked_hours = fields.Float("Hours Worked", readonly=True)
    overtime_hours = fields.Float("Extra Hours", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                (
                    SELECT
                        hra.id AS id,
                        department_id,
                        hra.employee_id AS employee_id,
                        hra.check_in AS check_in,
                        hra.worked_hours AS worked_hours,
                        coalesce(ot.duration, 0) as overtime_hours
                    FROM
                        hr_attendance hra
                    LEFT JOIN
                        hr_employee employee
                            ON employee.id = hra.employee_id
                    LEFT JOIN
                        hr_attendance_overtime ot
                            ON ot.employee_id = hra.employee_id
                            AND ot.date = hra.check_in::date
                            AND adjustment is false
                )
            )
        """ % (self._table))
