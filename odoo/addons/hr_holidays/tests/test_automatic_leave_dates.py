# -*- coding: utf-8 -*-
from datetime import date, datetime

from odoo.tests.common import Form

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.exceptions import ValidationError


class TestAutomaticLeaveDates(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAutomaticLeaveDates, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Automatic Test',
            'time_type': 'leave',
            'requires_allocation': 'no',
            # Required for `request_unit_half` to be visible in the view
            'request_unit': 'half_day',
        })

    def test_no_attendances(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'No Attendances',
            'attendance_ids': [(5, 0, 0)],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_date_to = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

            self.assertEqual(leave_form.number_of_days_display, 0)
            self.assertEqual(leave_form.number_of_hours_text, '0 Hours')

    def test_single_attendance_on_morning_and_afternoon(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'simple morning + afternoon',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'name': 'monday lunch',
                                   'hour_from': 12,
                                   'hour_to': 13,
                                   'day_period': 'lunch',
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'name': 'monday afternoon',
                                   'hour_from': 13,
                                   'hour_to': 17,
                                   'day_period': 'afternoon',
                                   'dayofweek': '0',
                               })]
        })

        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_date_to = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

            self.assertEqual(leave_form.number_of_days_display, .5)
            self.assertEqual(leave_form.number_of_hours_text, '4 Hours')

            leave_form.request_date_from_period = 'pm'

            self.assertEqual(leave_form.number_of_days_display, .5)
            self.assertEqual(leave_form.number_of_hours_text, '4 Hours')

    def test_multiple_attendance_on_morning(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'multi morning',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning 1',
                                   'hour_from': 8,
                                   'hour_to': 10,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'duration_days': 0.25,
                               }),
                               (0, 0, {
                                   'name': 'monday morning 2',
                                   'hour_from': 10.25,
                                   'hour_to': 12.25,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'duration_days': 0.25,
                               }),
                               (0, 0, {
                                   'name': 'monday lunch',
                                   'hour_from': 12.25,
                                   'hour_to': 13,
                                   'day_period': 'lunch',
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'name': 'monday afternoon',
                                   'hour_from': 13,
                                   'hour_to': 17,
                                   'day_period': 'afternoon',
                                   'dayofweek': '0',
                                   'duration_days': 0.5,
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_date_to = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

            self.assertEqual(leave_form.number_of_days_display, .5)
            self.assertEqual(leave_form.number_of_hours_text, '4 Hours')

            leave_form.request_date_from_period = 'pm'

            self.assertEqual(leave_form.number_of_days_display, .5)
            self.assertEqual(leave_form.number_of_hours_text, '4 Hours')

    def test_attendance_on_morning(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'Morning only',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'Monday All day',
                                   'hour_from': 8,
                                   'hour_to': 16,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                               })],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_date_to = date(2019, 9, 2)
            leave_form.request_unit_half = True
            # Ask for morning
            leave_form.request_date_from_period = 'am'

            self.assertEqual(leave_form.number_of_days_display, 1)
            self.assertEqual(leave_form.number_of_hours_text, '8 Hours')

            # Ask for afternoon
            leave_form.request_date_from_period = 'pm'

            self.assertEqual(leave_form.number_of_days_display, 0)
            self.assertEqual(leave_form.number_of_hours_text, '0 Hours')

    def test_attendance_next_day(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'tuesday morning',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '1',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # does not work on mondays
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_date_to = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'


            self.assertEqual(leave_form.number_of_days_display, 0)
            self.assertEqual(leave_form.number_of_hours_text, '0 Hours')
            self.assertEqual(leave_form.date_from, datetime(2019, 9, 2, 6, 0, 0))
            self.assertEqual(leave_form.date_to, datetime(2019, 9, 2, 10, 0, 0))

    def test_attendance_previous_day(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # does not work on tuesdays
            leave_form.request_date_from = date(2019, 9, 3)
            leave_form.request_date_to = date(2019, 9, 3)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'


            self.assertEqual(leave_form.number_of_days_display, 0)
            self.assertEqual(leave_form.number_of_hours_text, '0 Hours')
            self.assertEqual(leave_form.date_from, datetime(2019, 9, 3, 6, 0, 0))
            self.assertEqual(leave_form.date_to, datetime(2019, 9, 3, 10, 0, 0))

    def test_2weeks_calendar(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'two_weeks_calendar': True,
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning odd week',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'week_type': '0',
                                   'duration_days': 0.5,
                               }),
                               (0, 0, {
                                   'name': 'monday morning even week',
                                   'hour_from': 10,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'week_type': '1',
                                   'duration_days': 0.25
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # even week, works 2 hours
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_date_to = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

            self.assertEqual(leave_form.number_of_days_display, 0.25)
            self.assertEqual(leave_form.number_of_hours_text, '2 Hours')
            self.assertEqual(leave_form.date_from, datetime(2019, 9, 2, 8, 0, 0))
            self.assertEqual(leave_form.date_to, datetime(2019, 9, 2, 10, 0, 0))

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # odd week, works 4 hours
            leave_form.request_date_from = date(2019, 9, 9)
            leave_form.request_date_to = date(2019, 9, 9)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

            self.assertEqual(leave_form.number_of_days_display, 0.5)
            self.assertEqual(leave_form.number_of_hours_text, '4 Hours')
            self.assertEqual(leave_form.date_from, datetime(2019, 9, 9, 6, 0, 0))
            self.assertEqual(leave_form.date_to, datetime(2019, 9, 9, 10, 0, 0))

    def test_2weeks_calendar_next_week(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'two_weeks_calendar': True,
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning odd week',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'week_type': '0',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # even week, does not work
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_date_to = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

            self.assertEqual(leave_form.number_of_days_display, 0)
            self.assertEqual(leave_form.number_of_hours_text, '0 Hours')
            self.assertEqual(leave_form.date_from, datetime(2019, 9, 2, 6, 0, 0))
            self.assertEqual(leave_form.date_to, datetime(2019, 9, 2, 10, 0, 0))
