# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HRAttendanceReport(models.Model):
    _name = "hr.attendance.report"
    _description = "Attendance Statistics"
    _auto = False

    department_id = fields.Many2one('hr.department', string="Department", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    check_in = fields.Date("Check In", readonly=True)
    worked_hours = fields.Float("Hours Worked", readonly=True)
    overtime_hours = fields.Float("Extra Hours", readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                (
                    SELECT
                        hra.id,
                        hr_employee.department_id,
                        hra.employee_id,
                        hra.check_in,
                        hra.worked_hours,
                        coalesce(ot.duration, 0) as overtime_hours
                    FROM (
                        SELECT
                            id,
                            row_number() over (partition by employee_id, CAST(check_in AS DATE)) as ot_check,
                            employee_id,
                            CAST(check_in as DATE) as check_in,
                            worked_hours
                        FROM
                            hr_attendance
                        ) as hra
                    LEFT JOIN
                        hr_employee
                            ON hr_employee.id = hra.employee_id
                    LEFT JOIN
                        hr_attendance_overtime ot
                            ON hra.ot_check = 1
                            AND ot.employee_id = hra.employee_id
                            AND ot.date = hra.check_in
                            AND ot.adjustment = FALSE
                )
            )
        """ % (self._table))
