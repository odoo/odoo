# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    l10n_fr_date_to = fields.Datetime('End Date For French Rules', readonly=True)

    def _compute_fr_number_of_days(self, employee, date_from, date_to, employee_calendar, company_calendar):
        self.ensure_one()

        self.l10n_fr_date_to = False
        # We can fill the holes using the company calendar as default
        # What we need to compute is how much we will need to push date_to in order to account for the lost days
        # This gets even more complicated in two_weeks_calendars
        def calendar_works_on_date(CalendarAttendance, calendar, date):
            """
            Returns whether the calendar has attendances planned for that day of the week
            """
            weektype = str(CalendarAttendance.get_week_type(date))
            dayofweek_str = str(date.weekday())
            return any(attendance.dayofweek == dayofweek_str and\
                    (not calendar.two_weeks_calendar or attendance.week_type == weektype)\
                    for attendance in calendar.attendance_ids)

        CalendarAttendance = self.env['resource.calendar.attendance']
        if self.request_unit_half:
            # In normal workflows request_unit_half implies that date_from and date_to are the same
            # request_unit_half allows us to choose between `am` and `pm`
            # In a case where we work from mon-wed and request a half day in the morning
            # we do not want to push date_to since the next work attendance is actually in the afternoon
            date_from_weektype = str(CalendarAttendance.get_week_type(date_from))
            date_from_dayofweek = str(date_from.weekday())
            # Fetch the attendances we care about
            attendance_ids = employee_calendar.attendance_ids.filtered(lambda a:
                a.dayofweek == date_from_dayofweek and\
                (not employee_calendar.two_weeks_calendar or a.week_type == date_from_weektype))
            if len(attendance_ids) == 2 and self.request_date_from_period == 'am':
                # The employee took the morning off on a day where he works the afternoon aswell
                attendance = attendance_ids[0] if attendance_ids[0].day_period == 'morning' else attendance_ids[1]
                return {'days': 0.5, 'hours': attendance.hour_to - attendance.hour_from}
        # Check calendars for working days until we find the right target, start at date_to + 1 day
        # Postpone date_target until the next working day
        date_target = date_to + relativedelta(days=1)
        counter = 0
        while not calendar_works_on_date(CalendarAttendance, employee_calendar, date_target):
            date_target += relativedelta(days=1)
            counter += 1
            # Check that we aren't running an infinite loop (it would mean that employee_calendar is empty and
            # company_calendar works every day)
            # Allow up to 14 days for two weeks calendars.
            if counter > 14:
                # Default behaviour
                result = employee._get_work_days_data_batch(date_from, date_to, calendar=employee_calendar)[employee.id]
                if self.request_unit_half and result['hours'] > 0:
                    result['days'] = 0.5
                return result
        date_target = datetime.combine(date_target.date(), datetime.min.time())
        self.l10n_fr_date_to = date_target
        return employee._get_work_days_data_batch(date_from, date_target, calendar=company_calendar)[employee.id]

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """
        In french time off laws, if an employee has a part time contract, when taking time off
        before one of his off day (compared to the company's calendar) it should also count the time
        between the time off and the next calendar work day/company off day (weekends).

        For example take an employee working mon-wed in a company where the regular calendar is mon-fri.
        If the employee were to take a time off ending on wednesday, the legal duration would count until friday.

        Returns a dict containing two keys: 'days' and 'hours' with the value being the duration for the requested time period.
        """
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id).sudo()
            company = employee.company_id
            if company.country_id.code == 'FR' and company.time_off_reference_calendar:
                calendar = self._get_calendar()
                if calendar and calendar != company.time_off_reference_calendar:
                    return self._compute_fr_number_of_days(employee, date_from, date_to, calendar, company.time_off_reference_calendar)
        return super()._get_number_of_days(date_from, date_to, employee_id)
