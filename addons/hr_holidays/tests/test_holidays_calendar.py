# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta, datetime

from odoo.addons.base.tests.common import HttpCase
from odoo.tests.common import tagged
from odoo.tests.common import users
from odoo.exceptions import ValidationError


from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install', 'holiday_calendar')
class TestHolidaysCalendar(HttpCase, TestHrHolidaysCommon):

    @users('enguerran')
    def test_hours_time_off_request_calendar_view(self):
        """
        Testing the flow of clicking on a day, save the leave request directly
        and verify that the start/end time are correctly set.
        """
        self.env.user.tz = 'UTC'
        first_day_of_year = date(date.today().year, 1, 1)
        days_to_thursday = (3 - first_day_of_year.weekday()) % 7
        first_thursday_of_year = first_day_of_year + timedelta(days=days_to_thursday)

        leave = self.env['hr.leave'].new({
            'name': 'Reference Holiday',
            'employee_id': self.employee_emp.id,
            'request_date_from': first_thursday_of_year,
            'request_date_to': first_thursday_of_year,
        })
        leave._compute_date_from_to()
        expected_leave_start = leave.date_from.hour
        expected_leave_end = leave.date_to.hour

        # Tour that takes a leave on the first thursday of the year.
        self.start_tour('/odoo', 'time_off_request_calendar_view', login='enguerran')

        last_leave = self.env['hr.leave'].search([('employee_id.id', '=', self.employee_emp.id)]).sorted(lambda leave: leave.create_date)[-1]
        self.assertEqual(last_leave.date_from.weekday(), 3, "It should be Thursday")
        self.assertEqual(last_leave.date_from.hour, expected_leave_start, "Wrong start of the day")
        self.assertEqual(last_leave.date_to.hour, expected_leave_end, "Wrong end of the day")

    def test_timezone_calendar_event_single_day(self):
        """
        Test that single-day time off requests have a single day display in calendar
        """

        leave_type, leave_type_half = self.env['hr.work.entry.type'].create([
            {
                'name': 'Test Leave Type',
                'code': 'Test Leave Type',
                'requires_allocation': False,
                'leave_validation_type': 'no_validation',
                'create_calendar_meeting': True,
            },
            {
                'name': 'Test Leave Type Half Day',
                'code': 'Test Leave Type Half Day',
                'requires_allocation': False,
                'leave_validation_type': 'no_validation',
                'create_calendar_meeting': True,
                'request_unit': 'half_day',
            },
        ])

        # case 1: full day in Los/Angeles tz

        test_date = date(2025, 4, 22)
        self.employee_emp.user_id.tz = 'America/Los_Angeles'
        leave = self.env['hr.leave'].create({
            'name': 'Single Day Leave',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': leave_type.id,
            'request_date_from': test_date,
            'request_date_to': test_date,
        })

        leave.action_approve()

        self.assertEqual(leave.meeting_id.allday, True)
        self.assertEqual(leave.meeting_id.start_date, test_date,
                        f"Meeting start date should be {test_date}")
        self.assertEqual(leave.meeting_id.stop_date, test_date,
                        f"Meeting end date should be {test_date}")

        # case 2: half day in Los/Angeles tz

        test_date_half = date(2025, 4, 23)

        leave_half = self.env['hr.leave'].create({
            'name': 'Half Day Leave LA',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': leave_type_half.id,
            'request_date_from': test_date_half,
            'request_date_to': test_date_half,
            'request_date_from_period': 'pm',
            'request_date_to_period': 'pm',
        })

        leave_half.action_approve()

        self.assertEqual(leave_half.meeting_id.allday, False)
        self.assertEqual(leave_half.meeting_id.start, leave_half.date_from)
        self.assertEqual(leave_half.meeting_id.stop, leave_half.date_to)

    def test_overlapping_refused_time_off_approval(self):
        """
        Test that a refused time off request shows a warning message
        when another approved request exists for the same period.
        """
        leave_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Leave Type',
            'code': "TEST",
            'requires_allocation': False,
            'request_unit': 'day',
            'leave_validation_type': 'no_validation',
            'allow_request_on_top': False,
        })
        test_date = date(2025, 4, 22)

        # Now create leave requests
        leave_request_a = self.env['hr.leave'].create({
            'name': 'First Time Off Request',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': leave_type.id,
            'request_date_from': test_date,
            'request_date_to': test_date,
        })
        leave_request_a.action_approve()
        leave_request_a.action_refuse()
        leave_request_b = self.env['hr.leave'].create({
            'name': 'Second Time Off Request',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': leave_type.id,
            'request_date_from': test_date,
            'request_date_to': test_date,
        })
        leave_request_b.action_approve()
        with self.assertRaises(ValidationError):
            leave_request_a.action_approve()

    def test_half_day_and_hours_based_leave_on_same_day(self):
        """ Checks that an employee can book a hours-based time off in the afternoon if they already booked a half-day
        time off in the morning."""
        hours_time_off_type, half_days_time_off_type = self.env['hr.work.entry.type'].create([{
            'name': 'hours based time off',
            'code': 'HPTO',
            'count_as': 'absence',
            'requires_allocation': False,
            'unit_of_measure': 'hour',
            'request_unit': 'hour',
            'leave_validation_type': 'no_validation',
        },
        {
            'name': 'half-day based time off',
            'code': 'HDPTO',
            'count_as': 'absence',
            'requires_allocation': False,
            'unit_of_measure': 'hour',
            'request_unit': 'half_day',
            'leave_validation_type': 'no_validation',
        }])
        _, hours_time_off = self.env['hr.leave'].with_user(self.user_hruser).create([
        {
            'name': 'Leave 2',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': half_days_time_off_type.id,
            'request_date_from': datetime(2026, 8, 21, 8, 0, 0),
            'request_date_to': datetime(2026, 8, 21, 12, 0, 0),
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
            'request_duration': 'am'
        }, {
            'name': 'Leave 1',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': hours_time_off_type.id,
            'request_date_from': date(2026, 8, 21),
            'request_date_to': date(2026, 8, 21),
            'request_date_hour_from': datetime(2026, 8, 21, 15, 0, 0),
            'request_date_hour_to': datetime(2026, 8, 21, 16, 0, 0),
            'number_of_hours': 1,
        }])
        self.assertEqual(hours_time_off.request_hour_from, 17)  # converted to employee tz
        self.assertEqual(hours_time_off.request_hour_to, 18)
