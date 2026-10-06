from datetime import date, datetime

from odoo.fields import Command
from odoo.tests import tagged, Form

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestAutomaticLeaveDates(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAutomaticLeaveDates, cls).setUpClass()
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Automatic Test',
            'code': 'Automatic Test',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'half_day',
            'unit_of_measure': 'day',
        })

    def test_no_attendances(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'No Attendances',
            'attendance_ids': [(5, 0, 0)],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
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
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'hour_from': 13,
                                   'hour_to': 17,
                                   'dayofweek': '0',
                               })]
        })

        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
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
                                   'hour_from': 8,
                                   'hour_to': 10,
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'hour_from': 10.25,
                                   'hour_to': 12.25,
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'hour_from': 13,
                                   'hour_to': 17,
                                   'dayofweek': '0',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
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
                                   'hour_from': 8,
                                   'hour_to': 16,
                                   'dayofweek': '0',
                               })],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_date_to = date(2019, 9, 2)
            # Ask for morning
            leave_form.request_date_from_period = 'am'
            leave_form.request_date_to_period = 'am'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

            # Ask for afternoon
            leave_form.request_date_from_period = 'pm'
            leave_form.request_date_to_period = 'pm'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

    def test_attendance_full_day(self):
        calendar = self.env["resource.calendar"].create({
            "name": "Full Days",
            "attendance_ids": [
                Command.clear(),
                Command.create({
                    "hour_from": 8,
                    "hour_to": 16,
                    "dayofweek": "0",
                }),
            ],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(
            self.env["hr.leave"].with_context(default_employee_id=employee.id)
        ) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
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
            "attendance_ids": [
                Command.clear(),
                Command.create({
                    "duration_hours": 8,
                    "dayofweek": "0"}),
            ],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(
            self.env["hr.leave"].with_context(default_employee_id=employee.id)
        ) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
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

    def test_attendance_based_on_duration_full_day(self):
        calendar = self.env["resource.calendar"].create({
            "name": "Full Days",
            "attendance_ids": [
                Command.clear(),
                Command.create({
                    "duration_hours": 6,  # hour_from: 9, hour_to: 15
                    "dayofweek": "0",
                }),
            ],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(
            self.env["hr.leave"].with_context(default_employee_id=employee.id)
        ) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
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

    def test_time_off_half_day_duration_based_calendar(self):
        attendance_ids = []
        for dayofweek in ['0', '1', '2', '3', '4']:
            attendance_ids += [
                Command.create({
                    'dayofweek': dayofweek,
                    'duration_hours': 3.36,
                    'day_period': 'morning',
                }),
                Command.create({
                    'dayofweek': dayofweek,
                    'duration_hours': 3.36,
                    'day_period': 'afternoon',
                }),
            ]

        calendar = self.env['resource.calendar'].create({
            'name': 'Duration based calendar',
            'attendance_ids': attendance_ids,
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        leave = self.env['hr.leave'].create({
            'name': 'Full week half day leave',
            'employee_id': employee.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2026, 4, 20),
            'request_date_to': date(2026, 4, 24),
            'request_date_from_period': 'am',
            'request_date_to_period': 'pm',
        })

        self.assertEqual(leave.number_of_days, 5)

    def test_attendance_next_day(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'dayofweek': '1',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
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
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'dayofweek': '0',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.work_entry_type_id = self.work_entry_type
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
<<<<<<< bd63e51bf72fa9c1d4a923ce8fe93b5d7f317974
||||||| 9de359240a7dfa06dd900a9d61c3b623e6a97527

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
=======

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

    def test_hour_leave_hours_recomputed_when_dates_change(self):
        self.leave_type.request_unit = 'hour'
        calendar = self.env['resource.calendar'].create({
            'name': 'Variable Hours',
            'attendance_ids': [
                Command.clear(),
                Command.create({
                    'name': 'Monday Morning',
                    'dayofweek': '0',
                    'hour_from': 7.5,
                    'hour_to': 12,
                    'day_period': 'morning',
                }),
                Command.create({
                    'name': 'Monday Afternoon',
                    'dayofweek': '0',
                    'hour_from': 13,
                    'hour_to': 16.5,
                    'day_period': 'afternoon',
                }),
                Command.create({
                    'name': 'Friday Morning',
                    'dayofweek': '4',
                    'hour_from': 7.5,
                    'hour_to': 13.25,
                    'day_period': 'morning',
                }),
            ],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2025, 1, 3)
            leave_form.request_date_to = date(2025, 1, 3)

            self.assertEqual(leave_form.request_hour_from, 7.5)
            self.assertEqual(leave_form.request_hour_to, 13.25)

            leave_form.request_date_to = date(2025, 1, 6)
            leave_form.request_date_from = date(2025, 1, 6)

            self.assertEqual(leave_form.request_hour_from, 7.5)
            self.assertEqual(leave_form.request_hour_to, 16.5)
>>>>>>> 0ea28dbaec638007a54cf69191b055dcb21c1ba2
