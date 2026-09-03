from datetime import date, datetime

from odoo.fields import Command
from odoo.tests import Form

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestAutomaticLeaveDates(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAutomaticLeaveDates, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Automatic Test',
            'time_type': 'leave',
            'requires_allocation': False,
            'request_unit': 'half_day',
        })
        cls.leave_type_hour = cls.env['hr.leave.type'].create({
            'name': 'Automatic Test (Hours)',
            'time_type': 'leave',
            'requires_allocation': False,
            'request_unit': 'hour',
        })
        cls.leave_type_hour_incl_public_holidays = cls.env['hr.leave.type'].create({
            'name': 'Hours with working day on public holiday',
            'time_type': 'leave',
            'requires_allocation': False,
            'request_unit': 'hour',
            'include_public_holidays_in_duration': True,
        })
        cls.calendar_duration_based = cls.env['resource.calendar'].create({
            'name': 'Duration based calendar',
            'duration_based': True,
            'attendance_ids': [
                Command.create({
                    'name': day_name, 'dayofweek': dayofweek, 'duration_hours': 8, 'day_period': 'full_day',
                })
                for dayofweek, day_name in [('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday')]
            ],
        })
        cls.employee_emp.resource_calendar_id = cls.calendar_duration_based
        cls.employee_hruser.resource_calendar_id = cls.calendar_duration_based
        cls.employee_hrmanager.resource_calendar_id = cls.calendar_duration_based

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
            leave_form.request_date_from_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0)
        self.assertEqual(leave.number_of_hours, 0)

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
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

            leave_form.request_date_from_period = 'pm'
            leave_form.request_date_to_period = 'pm'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

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
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

            leave_form.request_date_from_period = 'pm'
            leave_form.request_date_to_period = 'pm'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

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
            # Ask for morning
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 1)
            self.assertEqual(leave_form.record.number_of_hours, 8)

            # Ask for afternoon
            leave_form.request_date_from_period = 'pm'
            leave_form.request_date_to_period = 'pm'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 0)
            self.assertEqual(leave_form.record.number_of_hours, 0)

    def test_attendance_full_day(self):
        calendar = self.env["resource.calendar"].create({
            "name": "Full Days",
            "attendance_ids": [
                Command.clear(),
                Command.create({
                    "name": "Monday",
                    "hour_from": 8,
                    "hour_to": 16,
                    "day_period": "full_day",
                    "dayofweek": "0",
                }),
            ],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(
            self.env["hr.leave"].with_context(default_employee_id=employee.id)
        ) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)  # Monday
            leave_form.request_date_to = date(2019, 9, 2)  # Monday

            # Ask for morning
            leave_form.request_date_from_period = "am"
            leave_form.request_date_to_period = "am"

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 0.5)
            self.assertEqual(leave_form.record.number_of_hours, 4)
            # dates are checked in UTC that why -2
            self.assertEqual(leave_form.record.date_from, datetime(2019, 9, 2, 6, 0, 0))
            self.assertEqual(leave_form.record.date_to, datetime(2019, 9, 2, 10, 0, 0))

            # Ask for afternoon
            leave_form.request_date_from_period = "pm"
            leave_form.request_date_to_period = "pm"

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 0.5)
            self.assertEqual(leave_form.record.number_of_hours, 4)
            # dates are checked in UTC that why -2
            self.assertEqual(leave_form.record.date_from, datetime(2019, 9, 2, 10, 0, 0))
            self.assertEqual(leave_form.record.date_to, datetime(2019, 9, 2, 14, 0, 0))

    def test_attendance_based_on_duration(self):
        calendar = self.env["resource.calendar"].create({
            "name": "Full Days",
            "duration_based": True,
            "attendance_ids": [
                Command.clear(),
                Command.create({
                    "name": "Monday Morning",
                    "duration_hours": 5,  # hour_from: 7, hour_to: 12
                    "day_period": "morning",
                    "dayofweek": "0"}),
                Command.create({
                    "name": "Monday Afternoon",
                    "duration_hours": 3,  # hour_from: 12, hour_to: 15
                    "day_period": "afternoon",
                    "dayofweek": "0"}),
            ],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(
            self.env["hr.leave"].with_context(default_employee_id=employee.id)
        ) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)  # Monday
            leave_form.request_date_to = date(2019, 9, 2)  # Monday

            # Ask for morning
            leave_form.request_date_from_period = "am"
            leave_form.request_date_to_period = "am"

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 0.5)
            self.assertEqual(leave_form.record.number_of_hours, 5)
            # dates are checked in UTC that why -2
            self.assertEqual(leave_form.record.date_from, datetime(2019, 9, 2, 5, 0, 0))
            self.assertEqual(leave_form.record.date_to, datetime(2019, 9, 2, 10, 0, 0))

            # Ask for afternoon
            leave_form.request_date_from_period = "pm"
            leave_form.request_date_to_period = "pm"

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 0.5)
            self.assertEqual(leave_form.record.number_of_hours, 3)
            # dates are checked in UTC that why -2
            self.assertEqual(leave_form.record.date_from, datetime(2019, 9, 2, 10, 0, 0))
            self.assertEqual(leave_form.record.date_to, datetime(2019, 9, 2, 13, 0, 0))

    def test_attendance_based_on_duration_full_day(self):
        calendar = self.env["resource.calendar"].create({
            "name": "Full Days",
            "duration_based": True,
            "attendance_ids": [
                Command.clear(),
                Command.create({
                    "name": "Monday",
                    "duration_hours": 6,  # hour_from: 9, hour_to: 15
                    "day_period": "full_day",
                    "dayofweek": "0",
                }),
            ],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(
            self.env["hr.leave"].with_context(default_employee_id=employee.id)
        ) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)  # Monday
            leave_form.request_date_to = date(2019, 9, 2)  # Monday

            # Ask for morning
            leave_form.request_date_from_period = "am"
            leave_form.request_date_to_period = "am"

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 0.5)
            self.assertEqual(leave_form.record.number_of_hours, 3)
            # dates are checked in UTC that why -2
            self.assertEqual(leave_form.record.date_from, datetime(2019, 9, 2, 7, 0, 0))
            self.assertEqual(leave_form.record.date_to, datetime(2019, 9, 2, 10, 0, 0))

            # Ask for afternoon
            leave_form.request_date_from_period = "pm"
            leave_form.request_date_to_period = "pm"

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 0.5)
            self.assertEqual(leave_form.record.number_of_hours, 3)
            # dates are checked in UTC that why -2
            self.assertEqual(leave_form.record.date_from, datetime(2019, 9, 2, 10, 0, 0))
            self.assertEqual(leave_form.record.date_to, datetime(2019, 9, 2, 13, 0, 0))

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
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0)
        self.assertEqual(leave.number_of_hours, 0)
        self.assertEqual(leave.date_from, datetime(2019, 9, 2, 6, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 2, 10, 0, 0))

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
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0)
        self.assertEqual(leave.number_of_hours, 0)
        self.assertEqual(leave.date_from, datetime(2019, 9, 3, 6, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 3, 10, 0, 0))

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
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0.25)
        self.assertEqual(leave.number_of_hours, 2)
        self.assertEqual(leave.date_from, datetime(2019, 9, 2, 8, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 2, 10, 0, 0))

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # odd week, works 4 hours
            leave_form.request_date_from = date(2019, 9, 9)
            leave_form.request_date_to = date(2019, 9, 9)
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0.5)
        self.assertEqual(leave.number_of_hours, 4)
        self.assertEqual(leave.date_from, datetime(2019, 9, 9, 6, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 9, 10, 0, 0))

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
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0)
        self.assertEqual(leave.number_of_hours, 0)
        self.assertEqual(leave.date_from, datetime(2019, 9, 2, 6, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 2, 10, 0, 0))

    def test_attendance_based_on_duration_hours(self):
        # Test that duration-based calendars allow leave at any hour of the day,
        # without being bound to any specific time period.
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type_hour.id,
            'request_date_from': date(2026, 2, 4),
            'request_date_to': date(2026, 2, 4),
            'request_hour_from': 4.0,
            'request_hour_to': 7.0,
        })
        self.assertEqual(leave.number_of_hours, 3)
        self.assertEqual(leave.number_of_days, 0.375)

    def test_duration_based_hours_with_public_holiday(self):
        calendar = self.calendar_duration_based

        self.env['resource.calendar.leaves'].create({
            'name': 'Test Public Holiday',
            'date_from': datetime(2026, 2, 4, 3, 0, 0),
            'date_to': datetime(2026, 2, 4, 15, 0, 0),
            'calendar_id': calendar.id,
            'time_type': 'leave',
        })

        # Leave fully within PH (8AM-3PM Brussels) → 0 hours
        leave1 = self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type_hour.id,
            'request_date_from': date(2026, 2, 4),
            'request_date_to': date(2026, 2, 4),
            'request_hour_from': 8.0,
            'request_hour_to': 15.0,
        })
        self.assertEqual(leave1.number_of_hours, 0)
        self.assertEqual(leave1.number_of_days, 0)

        # Same hours, include_public_holidays_in_duration=True → 7 hours
        leave2 = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.leave_type_hour_incl_public_holidays.id,
            'request_date_from': date(2026, 2, 4),
            'request_date_to': date(2026, 2, 4),
            'request_hour_from': 8.0,
            'request_hour_to': 15.0,
        })
        self.assertEqual(leave2.number_of_hours, 7)
        self.assertAlmostEqual(leave2.number_of_days, 0.875)

        # Leave after PH (5PM-8PM Brussels) → 3 hours
        leave3 = self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type_hour.id,
            'request_date_from': date(2026, 2, 4),
            'request_date_to': date(2026, 2, 4),
            'request_hour_from': 17.0,
            'request_hour_to': 20.0,
        })
        self.assertEqual(leave3.number_of_hours, 3)
        self.assertAlmostEqual(leave3.number_of_days, 0.375)

    def test_multi_day_leave_hours_duration_based_calendar(self):
        calendar = self.calendar_duration_based
        tuesday_attendance = calendar.attendance_ids.filtered(lambda a: a.dayofweek == '1')

        # Monday 2026-04-20 18:00 -> Wednesday 2026-04-22 03:00:
        # Monday 18:00-24:00 = 6h, Tuesday fully covered = 8h (configured), Wednesday 00:00-03:00 = 3h
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type_hour.id,
            'request_date_from': date(2026, 4, 20),
            'request_date_to': date(2026, 4, 22),
            'request_hour_from': 18,
            'request_hour_to': 3,
        })
        self.assertEqual(leave.number_of_hours, 17.0)
        self.assertEqual(leave.number_of_days, 2.125)

        # Reduce Tuesday's configured hours to 4: the fully covered day must count those 4 hours
        tuesday_attendance.duration_hours = 4
        leave2 = self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type_hour.id,
            'request_date_from': date(2026, 4, 27),
            'request_date_to': date(2026, 4, 29),
            'request_hour_from': 18,
            'request_hour_to': 3,
        })
        self.assertEqual(leave2.number_of_hours, 13.0)
        self.assertEqual(leave2.number_of_days, 2.125)

    def test_duration_based_half_day_with_public_holiday(self):
        calendar = self.calendar_duration_based

        # Public Holiday on the full day in between (Tuesday) of a
        # Monday(pm)->Wednesday(am) half day leave: that day should be excluded.
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday (Tuesday)',
            'date_from': datetime(2026, 4, 21, 0, 0, 0),
            'date_to': datetime(2026, 4, 21, 23, 59, 59),
            'calendar_id': calendar.id,
            'time_type': 'leave',
        })
        leave_middle_holiday = self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2026, 4, 20),
            'request_date_to': date(2026, 4, 22),
            'request_date_from_period': 'pm',
            'request_date_to_period': 'am',
        })
        self.assertEqual(leave_middle_holiday.number_of_days, 1)
        self.assertEqual(leave_middle_holiday.number_of_hours, 8)

        # With "Ignore Public Holidays" enabled on the leave type, the same
        # public holiday should not be excluded and the full duration should count.
        leave_type_half_day_incl_public_holidays = self.env['hr.leave.type'].create({
            'name': 'Half-Day with working day on public holiday',
            'time_type': 'leave',
            'requires_allocation': False,
            'request_unit': 'half_day',
            'include_public_holidays_in_duration': True,
        })
        leave_include_holidays = self.env['hr.leave'].create({
            'employee_id': self.employee_hrmanager.id,
            'holiday_status_id': leave_type_half_day_incl_public_holidays.id,
            'request_date_from': date(2026, 4, 20),
            'request_date_to': date(2026, 4, 22),
            'request_date_from_period': 'pm',
            'request_date_to_period': 'am',
        })
        self.assertEqual(leave_include_holidays.number_of_days, 2)
        self.assertEqual(leave_include_holidays.number_of_hours, 16)
