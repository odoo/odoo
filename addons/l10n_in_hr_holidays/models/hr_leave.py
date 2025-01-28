# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.rrule import rrule, DAILY
from datetime import datetime, timedelta

from odoo import models, fields


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    l10n_in_contains_sandwich_leaves = fields.Boolean()

    def _get_no_worked_days_list(self, request_date_from, request_date_to, public_holidays, calendar):
        prev_was_a_worked_day = True
        continue_no_worked_days_list = []
        start_day_list = stop_day_list = request_date_from

        for day in rrule(DAILY, dtstart=request_date_from, until=request_date_to):
            if calendar._works_on_date(day) and not any(
                datetime.date(holiday['date_from']) <= day.date() <= datetime.date(holiday['date_to'])
                for holiday in public_holidays
            ):
                if prev_was_a_worked_day:
                    continue
                prev_was_a_worked_day = True
                stop_day_list = day + timedelta(days=-1)
                continue_no_worked_days_list.append((start_day_list, stop_day_list))
            else:
                if prev_was_a_worked_day:
                    start_day_list = day
                    prev_was_a_worked_day = False
                if day.date() == request_date_to:
                    stop_day_list = day
                    continue_no_worked_days_list.append((start_day_list, stop_day_list))

        return continue_no_worked_days_list

    def _l10n_in_apply_sandwich_rule(self, public_holidays, employee_leaves):
        self.ensure_one()
        calendar = self.employee_id._get_calendars(self.request_date_from)[self.employee_id.id]
        duration = (self.request_date_to - self.request_date_from).days + 1
        no_worked_days_list = self._get_no_worked_days_list(self.request_date_from, self.request_date_to, public_holidays, calendar)
        if no_worked_days_list:
            for (start, stop) in no_worked_days_list:
                if start.date() > self.request_date_from and stop.date() < self.request_date_to:
                    continue
                duration -= ((stop - start).days) + 1
        number_of_no_working_days_before = 0
        number_of_no_working_days_after = 0
        while True:
            day = self.request_date_from - timedelta(days=number_of_no_working_days_before + 1)
            if calendar._works_on_date(day) and not any(
                datetime.date(holiday['date_from']) <= day <= datetime.date(holiday['date_to'])
                for holiday in public_holidays
            ):
                break
            number_of_no_working_days_before += 1
        for day in rrule(DAILY, dtstart=self.request_date_to + timedelta(days=1)):
            if calendar._works_on_date(day) and not any(
                datetime.date(holiday['date_from']) <= day.date() <= datetime.date(holiday['date_to'])
                for holiday in public_holidays
            ):
                break
            number_of_no_working_days_after += 1
        date_from_to_check = self.request_date_from - timedelta(days=number_of_no_working_days_before +1)
        date_to_to_check = self.request_date_to + timedelta(days=number_of_no_working_days_after +1)
        for employee_leave in employee_leaves:
            if employee_leave.l10n_in_contains_sandwich_leaves:
                continue
            if employee_leave.request_date_from <= date_from_to_check <= employee_leave.request_date_to:
                duration += number_of_no_working_days_before
                break
            if employee_leave.request_date_from <= date_to_to_check <= employee_leave.request_date_to:
                duration += number_of_no_working_days_after
                break
        return duration

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = super()._get_durations(check_leave_type, resource_calendar)
        indian_leaves = self.filtered(lambda c: c.company_id.country_id.code == 'IN')
        if not indian_leaves:
            return result

        public_holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', indian_leaves.company_id.ids),
        ])
        leaves_by_employee = dict(self._read_group(
            domain=[
                ('id', 'not in', self.ids),
                ('employee_id', 'in', self.employee_id.ids),
                ('state', 'not in', ['cancel', 'refuse']),
                ('leave_type_request_unit', '=', 'day'),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        for leave in indian_leaves:
            if leave.holiday_status_id.l10n_in_is_sandwich_leave:
                days, hours = result[leave.id]
                updated_days = leave._l10n_in_apply_sandwich_rule(public_holidays, leaves_by_employee.get(leave.employee_id, []))
                result[leave.id] = (updated_days, hours)
                if updated_days:
                    leave.l10n_in_contains_sandwich_leaves = updated_days != days
            else:
                leave.l10n_in_contains_sandwich_leaves = False
        return result
