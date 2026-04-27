# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from pytz import UTC, utc

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import float_is_zero

from odoo.addons.resource.models.utils import timezone_datetime


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    color = fields.Integer("Color", compute='_compute_color')
    overtime_progress = fields.Float(compute="_compute_overtime_progress")

    def _compute_overtime_progress(self):
        for attendance in self:
            if not float_is_zero(attendance.worked_hours, precision_digits=2):
                attendance.overtime_progress = 100 - ((attendance.overtime_hours / attendance.worked_hours) * 100)
            else:
                attendance.overtime_progress = 100

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if not self.env.user._is_internal():
            return {}
        if field == 'employee_id':
            start, stop = utc.localize(start), utc.localize(stop)
            return self._gantt_progress_bar_employee_ids(res_ids, start, stop)
        raise NotImplementedError

    def _gantt_compute_max_work_hours_within_interval(self, employee, start, stop):
        """
        Compute the total work hours of the employee based on the intervals selected on the Gantt view.
        The calculation takes into account the working calendar (flexible or not).
        """
        return self.env['resource.calendar']._get_attendance_intervals_days_data(employee._employee_attendance_intervals(start, stop))['hours']

    def _get_gantt_progress_bar_domain(self, res_ids, start, stop):
        domain = [
            ('employee_id', 'in', res_ids),
            ('check_in', '>=', start),
            ('check_out', '<=', stop)
        ]
        return domain

    def _gantt_progress_bar_employee_ids(self, res_ids, start, stop):
        """
        Resulting display is worked hours / expected worked hours
        """
        values = {}
        worked_hours_group = self._read_group(
            self._get_gantt_progress_bar_domain(res_ids, start, stop),
            groupby=['employee_id'],
            aggregates=['worked_hours:sum']
        )
        employee_data = {emp.id: worked_hours for emp, worked_hours in worked_hours_group}
        employees = self.env['hr.employee'].browse(res_ids)
        for employee in employees:
            # Retrieve expected attendance for that employee
            values[employee.id] = {
                'value': employee_data.get(employee.id, 0),
                'max_value': self._gantt_compute_max_work_hours_within_interval(employee, start, stop),
                'is_fully_flexible_hours': employee.resource_id._is_fully_flexible(),
            }

        return values

    @api.model
    def get_gantt_data(self, domain, groupby, read_specification, limit=None, offset=0, unavailability_fields=[], progress_bar_fields=None, start_date=None, stop_date=None, scale=None):
        """
        We override get_gantt_data to allow the display of open-ended records,
        We also want to add in the gantt rows, the active emloyees that have a check in in the previous 60 days
        """

        domain = expression.AND([domain, self.env.context.get('active_domain', [])])
        open_ended_gantt_data = super().get_gantt_data(domain, groupby, read_specification, limit=limit, offset=offset, unavailability_fields=unavailability_fields, progress_bar_fields=progress_bar_fields, start_date=start_date, stop_date=stop_date, scale=scale)

        if self.env.context.get('gantt_start_date') and groupby and groupby[0] == 'employee_id':
            user_domain = self.env.context.get('user_domain')
            active_employees_domain = expression.AND([
                user_domain,
                [
                    '&',
                    ('check_out', '<', start_date),
                    ('check_in', '>', fields.Datetime.from_string(start_date) - relativedelta(days=60)),
                    ('employee_id', 'not in', [group['employee_id'][0] for group in open_ended_gantt_data['groups']]),
                    ('employee_id.active', '=', True),
                ]])
            previously_active_employees = super().get_gantt_data(active_employees_domain, groupby, read_specification, limit=None, offset=0, unavailability_fields=unavailability_fields, progress_bar_fields=progress_bar_fields, start_date=start_date, stop_date=stop_date, scale=scale)
            for group in previously_active_employees['groups']:
                del group['__record_ids']  # Records are not needed here
                open_ended_gantt_data['groups'].append(group)
                open_ended_gantt_data['length'] += 1
            if unavailability_fields:
                for field in open_ended_gantt_data['unavailabilities']:
                    open_ended_gantt_data['unavailabilities'][field] |= previously_active_employees['unavailabilities'][field]

        return open_ended_gantt_data

    @api.model
    def _gantt_unavailability(self, field, res_ids, start, stop, scale):
        if field != "employee_id":
            return super()._gantt_unavailability(field, res_ids, start, stop, scale)

        employees = self.env['hr.employee'].browse(res_ids)

        # Retrieve for each employee, their period linked to their calendars
        calendar_periods_by_employee = employees._get_calendar_periods(
            timezone_datetime(start),
            timezone_datetime(stop),
        )

        unavailable_intervals = employees.resource_id._get_unavailable_intervals(start, stop)

        result = {}
        for employee in employees:
            # When an employee doesn't have any calendar,
            # he is considered unavailable for the entire interval
            if employee not in calendar_periods_by_employee:
                result[employee.id] = [{
                    'start': start.astimezone(UTC),
                    'stop': stop.astimezone(UTC),
                }]
                continue

            intervals = unavailable_intervals.get(employee.resource_id.id, [])
            result[employee.id] = [
                {'start': inv[0], 'stop': inv[1]}
                for inv in intervals
            ]

        return result

    def action_open_details(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.attendance",
            "views": [[self.env.ref('hr_attendance.hr_attendance_view_form').id, "form"]],
            "res_id": self.id
        }
