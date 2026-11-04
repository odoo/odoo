# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class TimesheetAttendance(models.Model):
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
        self._cr.execute("""CREATE OR REPLACE VIEW %s AS (
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
                                WHERE calendar.id = employee.resource_calendar_id)
                    as DATE) as date,
                    hr_employee.company_id as company_id
                FROM hr_attendance
                LEFT JOIN hr_employee ON hr_employee.id = hr_attendance.employee_id
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
            ) AS t
            GROUP BY t.employee_id, t.date, t.company_id, t.emp_cost
            ORDER BY t.date
        )
        """ % self._table)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not orderby and groupby:
            orderby_list = [groupby] if isinstance(groupby, str) else groupby
            orderby_list = [field.split(':')[0] for field in orderby_list]
            orderby = ','.join([f"{field} desc" if field == 'date' else field for field in orderby_list])
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
