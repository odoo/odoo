# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class TimesheetAttendance(models.Model):
    _name = 'hr.timesheet.attendance.report'
    _auto = False
    _description = 'Timesheet Attendance Report'

    employee_id = fields.Many2one('hr.employee', readonly=True)
    date = fields.Date(readonly=True)
    total_timesheet = fields.Float("Timesheets Hours", readonly=True)
    total_attendance = fields.Float("Attendance Hours", readonly=True)
    total_difference = fields.Float("Hours Difference", readonly=True)
    timesheets_cost = fields.Float("Timesheet Cost", readonly=True)
    attendance_cost = fields.Float("Attendance Cost", readonly=True)
    cost_difference = fields.Float("Cost Difference", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

    @property
    def _table_query(self):
        time_off_where = ""
        if 'holiday_id' in self.env['account.analytic.line']._fields:
            time_off_where = """
                AND NOT EXISTS (
                    SELECT 1
                      FROM hr_leave
                      JOIN hr_leave_type ON hr_leave_type.id = hr_leave.holiday_status_id
                     WHERE hr_leave.id = ts.holiday_id
                       AND hr_leave_type.time_type = 'leave'
                )
                AND NOT EXISTS (
                    SELECT 1
                      FROM resource_calendar_leaves
                     WHERE resource_calendar_leaves.id = ts.global_leave_id
                       AND resource_calendar_leaves.time_type = 'leave'
                )"""
        return """
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
                WHERE ts.project_id IS NOT NULL%s
            ) AS t
            GROUP BY t.employee_id, t.date, t.company_id, t.emp_cost
            ORDER BY t.date
        """ % time_off_where

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not orderby and groupby:
            orderby_list = [groupby] if isinstance(groupby, str) else groupby
            orderby_list = [field.split(':')[0] for field in orderby_list]
            orderby = ','.join([f"{field} desc" if field == 'date' else field for field in orderby_list])
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
