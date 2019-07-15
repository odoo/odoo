# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TimesheetAttendance(models.Model):
    _name = 'hr.timesheet.attendance.report'
    _auto = False
    _description = 'Timesheet Attendance Report'

    user_id = fields.Many2one('res.users')
    date = fields.Date()
    total_timesheet = fields.Float()
    total_attendance = fields.Float()
    total_difference = fields.Float()

    @api.model_cr
    def init(self):
        self._cr.execute("DROP VIEW IF EXISTS hr_timesheet_attendance_report")
        self._cr.execute("""CREATE OR REPLACE VIEW %s AS (
            SELECT
                max(id) AS id,
                t.user_id,
                t.date,
                coalesce(sum(t.attendance), 0) AS total_attendance,
                coalesce(sum(t.timesheet), 0) AS total_timesheet,
                coalesce(sum(t.attendance), 0) - coalesce(sum(t.timesheet), 0) as total_difference
            FROM (
                SELECT
                    -hr_attendance.id AS id,
                    resource_resource.user_id AS user_id,
                    hr_attendance.worked_hours AS attendance,
                    NULL AS timesheet,
                    hr_attendance.check_in::date AS date
                FROM hr_attendance
                LEFT JOIN hr_employee ON hr_employee.id = hr_attendance.employee_id
                LEFT JOIN resource_resource on resource_resource.id = hr_employee.resource_id
            UNION ALL
                SELECT
                    ts.id AS id,
                    ts.user_id AS user_id,
                    NULL AS attendance,
                    ts.unit_amount AS timesheet,
                    ts.date AS date
                FROM account_analytic_line AS ts
                WHERE ts.project_id IS NOT NULL
            ) AS t
            GROUP BY t.user_id, t.date
            ORDER BY t.date
        )
        """ % self._table)
