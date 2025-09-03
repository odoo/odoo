# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class HrTimesheetAttendanceReport(models.Model):
    _name = 'hr.timesheet.attendance.report'
    _auto = False
    _description = 'Timesheet Attendance Report'

    employee_id = fields.Many2one('hr.employee', readonly=True)
    date = fields.Date(readonly=True)
    total_timesheet = fields.Float("Timesheets Time", readonly=True)
    total_attendance = fields.Float("Attendance Time", readonly=True)
    total_difference = fields.Float("Time Difference", readonly=True)
    timesheets_cost = fields.Float("Timesheet Cost", readonly=True)
    attendance_cost = fields.Float("Attendance Cost", readonly=True)
    cost_difference = fields.Float("Cost Difference", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE OR REPLACE VIEW %s AS (
            SELECT
                max(id) AS id,
                t.employee_id,
                t.date,
                t.company_id,
                coalesce(sum(t.attendance), 0) AS total_attendance,
                coalesce(sum(t.timesheet), 0) AS total_timesheet,
                coalesce(sum(t.attendance), 0) - coalesce(sum(t.timesheet), 0) as total_difference,
                NULLIF(sum(t.timesheet) * t.emp_cost, 0) as timesheets_cost,
                NULLIF(sum(t.attendance) * t.emp_cost, 0) as attendance_cost,
                NULLIF((coalesce(sum(t.attendance), 0) -  coalesce(sum(t.timesheet), 0)) * t.emp_cost, 0)  as cost_difference
            FROM (
                SELECT
                    -hr_attendance.id AS id,
                    hr_employee.hourly_cost AS emp_cost,
                    hr_attendance.employee_id AS employee_id,
                    hr_attendance.worked_hours AS attendance,
                    NULL AS timesheet,
                    CAST(hr_attendance.check_in
                            at time zone 'utc'
                            at time zone
                                (SELECT calendar.tz FROM resource_calendar as calendar
                                INNER JOIN hr_employee as employee ON employee.id = hr_attendance.employee_id
                                LEFT JOIN hr_version v ON v.id = employee.current_version_id
                                WHERE calendar.id = v.resource_calendar_id)
                    as DATE) as date,
                    hr_employee.company_id as company_id
                FROM hr_attendance
                LEFT JOIN hr_employee ON hr_employee.id = hr_attendance.employee_id
                WHERE check_in::date <= CURRENT_DATE
            UNION ALL
                SELECT
                    ts.id AS id,
                    hr_employee.hourly_cost AS emp_cost,
                    ts.employee_id AS employee_id,
                    NULL AS attendance,
                    ts.unit_amount AS timesheet,
                    ts.date AS date,
                    ts.company_id AS company_id
                FROM account_analytic_line AS ts
                LEFT JOIN hr_employee ON hr_employee.id = ts.employee_id
                WHERE ts.project_id IS NOT NULL
                  AND date <= CURRENT_DATE
            ) AS t
            GROUP BY t.employee_id, t.date, t.company_id, t.emp_cost
            ORDER BY t.date
        )
        """ % self._table)

    @api.model
    def formatted_read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None) -> list[dict]:
        if not order and groupby:
            order = ', '.join(f"{spec} DESC" if spec.startswith('date:') else spec for spec in groupby)
        return super().formatted_read_group(domain, groupby, aggregates, having=having, offset=offset, limit=limit, order=order)
