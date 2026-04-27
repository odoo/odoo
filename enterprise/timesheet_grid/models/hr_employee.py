# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime, time, timedelta
from pytz import timezone, UTC

from odoo import api, fields, models, _
from odoo.tools import float_round
from odoo.addons.resource.models.utils import sum_intervals, HOURS_PER_DAY
from odoo.exceptions import UserError


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _get_employees_working_hours(self, employees, start_datetime, end_datetime):

        # find working hours for the given period of employees with working calendar
        # Note: convert date str into datetime object. Time will be 00:00:00 and 23:59:59
        # respectively for date_start and date_stop, because we want the date_stop to be included.
        start_datetime = datetime.combine(fields.Date.from_string(start_datetime), time.min)
        end_datetime = datetime.combine(fields.Date.from_string(end_datetime), time.max)
        start_datetime = start_datetime.replace(tzinfo=UTC)
        end_datetime = end_datetime.replace(tzinfo=UTC)

        employees_work_days_data, _dummy = employees.sudo().resource_id._get_valid_work_intervals(start_datetime, end_datetime)

        return employees_work_days_data

    def _get_timesheet_manager_id_domain(self):
        group = self.env.ref('hr_timesheet.group_hr_timesheet_approver', raise_if_not_found=False)
        return [('groups_id', 'in', [group.id])] if group else []

    timesheet_manager_id = fields.Many2one(
        'res.users', string='Timesheet',
        compute='_compute_timesheet_manager', store=True, readonly=False,
        domain=_get_timesheet_manager_id_domain,
        help='Select the user responsible for approving "Timesheet" of this employee.\n'
             'If empty, the approval is done by a Timesheets > Administrator or a Timesheets > User: all timesheets (as determined in the users settings).')

    last_validated_timesheet_date = fields.Date(groups="hr_timesheet.group_timesheet_manager")

    @api.depends('parent_id')
    def _compute_timesheet_manager(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            manager = employee.parent_id.user_id
            if manager and manager.has_group('hr_timesheet.group_hr_timesheet_approver') and (employee.timesheet_manager_id == previous_manager or not employee.timesheet_manager_id):
                employee.timesheet_manager_id = manager
            elif not employee.timesheet_manager_id:
                employee.timesheet_manager_id = False

    def get_timesheet_and_working_hours(self, date_start, date_stop):
        """ Get the difference between the supposed working hour (based on resource calendar) and
            the timesheeted hours, for the given period `date_start` - `date_stop` (inclusives).
            :param date_start: start date of the period to check (date string)
            :param date_stop: end date of the period to check (date string)
            :returns dict: a dict mapping the employee_id with his timesheeted and working hours for the
                given period.
        """
        employees = self.filtered('resource_calendar_id')
        result = {i: dict(timesheet_hours=0.0, working_hours=0.0, date_start=date_start, date_stop=date_stop) for i in self.ids}
        if not employees:
            return result

        # find timesheeted hours of employees with working hours
        self.env.cr.execute("""
            SELECT A.employee_id as employee_id, sum(A.unit_amount) as amount_sum
            FROM account_analytic_line A
            WHERE A.employee_id IN %s AND date >= %s AND date <= %s
            GROUP BY A.employee_id
        """, (tuple(employees.ids), date_start, date_stop))
        for data_row in self.env.cr.dictfetchall():
            result[data_row['employee_id']]['timesheet_hours'] = float_round(data_row['amount_sum'], 2)

        employees_work_days_data = self._get_employees_working_hours(employees, date_start, date_stop)
        for employee in employees:
            working_hours = sum_intervals(employees_work_days_data[employee.resource_id.id])
            result[employee.id]['working_hours'] = float_round(working_hours, 2)
        return result

    def _count_daily_working_hours(self, date_start, date_stop):
        result = defaultdict(dict)
        # Change the type of the date from string to Date
        date_start_date = fields.Date.from_string(date_start)
        date_stop_date = min(fields.Date.from_string(date_stop), fields.Date.today())

        # Compute the difference between the starting and ending date
        delta = date_stop_date - date_start_date

        # Change the type of the date from date to datetime and add UTC as the timezone time standard
        tz = self.env.user.tz
        if not tz and len(mapped_tz := self.resource_id.mapped('tz')) == 1:
            tz = mapped_tz[0]
        tz = tz or 'UTC'
        datetime_min = timezone(tz).localize(datetime.combine(date_start_date, time.min)).astimezone(UTC)
        datetime_max = timezone(tz).localize(datetime.combine(date_stop_date, time.max)).astimezone(UTC)
        # Collect the number of hours that an employee should work according to their schedule without counting timeoff
        resource_work_intervals, dummy = self.resource_id._get_valid_work_intervals(datetime_min, datetime_max, compute_leaves=False)

        for employee in self:
            working_hours = resource_work_intervals[employee.resource_id.id]
            calendar = employee.resource_calendar_id
            if not calendar:
                # the employee without any resource calendar is supposed to work h24
                continue
            is_flexible_hours = False
            hours_per_day = HOURS_PER_DAY
            if calendar.flexible_hours:
                is_flexible_hours = True
                if not calendar:
                    calendar = employee.company_id.resource_calendar_id
                full_time_required_hours = calendar.full_time_required_hours
                if full_time_required_hours and delta.days > 0:
                   result[employee.id]['full_time_required_hours'] = round(full_time_required_hours / 7 * (delta.days + 1), 2)
                hours_per_day = calendar.hours_per_day or HOURS_PER_DAY
            for day_count in range(delta.days + 1):
                date = date_start_date + timedelta(days=day_count)
                if is_flexible_hours:
                    value = hours_per_day
                else:
                    value = sum(
                        (stop - start).total_seconds() / 3600
                        for start, stop, meta in working_hours
                        if start.date() == date
                    )
                result[employee.id][fields.Date.to_string(date)] = value

        return result

    def get_daily_working_hours(self, date_start, date_stop):
        return self._count_daily_working_hours(date_start, date_stop)

    def _get_timesheets_and_working_hours_query(self):
        return """
            SELECT aal.employee_id as employee_id, COALESCE(SUM(aal.unit_amount), 0) as worked_hours
            FROM account_analytic_line aal
            WHERE aal.employee_id IN %s AND date >= %s AND date <= %s AND project_id IS NOT NULL
            GROUP BY aal.employee_id
        """

    def get_timesheet_and_working_hours_for_employees(self, date_start, date_stop):
        """
        Method called by the timesheet avatar widget on the frontend in gridview to get information
        about the hours employees have worked and should work.

        :param date_start: date start of the interval to search
        :param state_stop: date stop of the interval to search
        :return: Dictionary of dictionary
                 for each employee id =>
                     number of units to work,
                     what unit type are we using
                     the number of worked units by the employees
        """
        result = {}
        uom = str(self.env.company.timesheet_encode_uom_id.name).lower()
        hours_per_day_per_employee = {}
        employees_work_days_data = {}

        if self:
            employees_work_days_data = self._get_employees_working_hours(self, date_start, date_stop)

        for employee in self:
            units_to_work = sum_intervals(employees_work_days_data[employee.resource_id.id])

            # Adjustments if we work with a different unit of measure
            if uom == 'days':
                calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
                hours_per_day_per_employee[employee.id] = calendar.hours_per_day
                units_to_work = units_to_work / hours_per_day_per_employee[employee.id]
                rounding = len(str(self.env.company.timesheet_encode_uom_id.rounding).split('.')[1])
                units_to_work = round(units_to_work, rounding)
            result[employee.id] = {'units_to_work': units_to_work, 'uom': uom, 'worked_hours': 0.0}

        query = self._get_timesheets_and_working_hours_query()
        self.env.cr.execute(query, (tuple(self.ids), date_start, date_stop))
        for data_row in self.env.cr.dictfetchall():
            worked_hours = data_row['worked_hours']
            if uom == 'days':
                worked_hours /= hours_per_day_per_employee[data_row['employee_id']]
                rounding = len(str(self.env.company.timesheet_encode_uom_id.rounding).split('.')[1])
                worked_hours = round(worked_hours, rounding)
            result[data_row['employee_id']]['worked_hours'] = worked_hours

        return result

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['timesheet_manager_id']

    def action_timesheet_from_employee(self):
        action = super().action_timesheet_from_employee()
        action['context']['group_expand'] = True
        return action

    def get_last_validated_timesheet_date(self):
        if self.env.user.has_group('hr_timesheet.group_timesheet_manager'):
            return {}

        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            raise UserError(_('You are not allowed to see timesheets.'))

        return {
            employee.id: employee.last_validated_timesheet_date
            for employee in self.sudo()
        }


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    timesheet_manager_id = fields.Many2one('res.users', string='Timesheet',
        help="User responsible of timesheet validation. Should be Timesheet Manager.")
