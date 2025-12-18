from datetime import date, datetime

from odoo.fields import Command
from odoo.tests import tagged, Form

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


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
