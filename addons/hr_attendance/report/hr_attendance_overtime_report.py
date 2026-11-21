# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrAttendanceOvertimeReport(models.TransientModel):
    _name = 'hr.attendance.overtime.report'
    _description = 'Overtime Report'
    _order = 'employee_id, date'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True,
        ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    date = fields.Date(string="Date", required=True, readonly=True)
    expected_hours = fields.Float(string="Expected Hours", readonly=True)
    worked_hours = fields.Float(string="Worked Hours", readonly=True)
    overtime_hours = fields.Float(string="Overtime", readonly=True,
        help="Worked hours minus expected hours. Negative when the employee worked less than expected.")

    @api.model
    def _get_report_employees(self):
        domain = [('company_id', 'in', self.env.companies.ids)]
        if not self.env.user.has_group('hr_attendance.group_hr_attendance_user'):
            domain.append(('attendance_manager_id', '=', self.env.uid))
        return self.env['hr.employee'].search(domain)

    @api.model
    def _get_expected_hours_by_day(self, employee, date_from, date_to):
        """Return the hours the employee is expected to work per local day between two dates,
        according to their working schedule (time off counted as absence deduced).

        :rtype: dict[date, float]
        """
        tz = ZoneInfo(employee._get_tz())
        intervals = employee._get_expected_attendances(
            datetime.combine(date_from, time.min, tz),
            datetime.combine(date_to, time.max, tz),
        )
        hours_by_day = defaultdict(float)
        for start, stop, _attendance in intervals:
            hours_by_day[start.astimezone(tz).date()] += (stop - start).total_seconds() / 3600
        return hours_by_day

    @api.model
    def _rebuild(self, employees, date_from, date_to):
        """Replace the current user's lines by one line per employee and day with expected or
        worked hours between two dates.

        Worked hours are those of the closed, not refused attendances, on their check-in day.
        """
        self.search([('create_uid', '=', self.env.uid)]).unlink()
        worked_groups = self.env['hr.attendance']._read_group(
            domain=[
                ('employee_id', 'in', employees.ids),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('check_out', '!=', False),
                ('state', '!=', 'refused'),
            ],
            groupby=['employee_id', 'date:day'],
            aggregates=['worked_hours:sum'],
        )
        worked_by_employee_day = {
            (employee, day): worked_hours for employee, day, worked_hours in worked_groups
        }

        vals_list = []
        for employee in employees:
            expected_by_day = self._get_expected_hours_by_day(employee, date_from, date_to)
            worked_days = {day for emp, day in worked_by_employee_day if emp == employee}
            for day in sorted(expected_by_day.keys() | worked_days):
                expected = expected_by_day.get(day, 0.0)
                worked = worked_by_employee_day.get((employee, day), 0.0)
                vals_list.append({
                    'employee_id': employee.id,
                    'date': day,
                    'expected_hours': expected,
                    'worked_hours': worked,
                    'overtime_hours': worked - expected,
                })
        return self.create(vals_list)

    @api.model
    def action_open_report(self):
        """Rebuild the lines of the last 12 months up to today, then open them."""
        today = fields.Date.today()
        self._rebuild(self._get_report_employees(), today - relativedelta(months=12, day=1), today)
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Overtime"),
            'res_model': 'hr.attendance.overtime.report',
            'view_mode': 'pivot,list',
            'domain': [('create_uid', '=', self.env.uid)],
        }
