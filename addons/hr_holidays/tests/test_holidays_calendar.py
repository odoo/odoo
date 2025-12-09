# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo.osv import expression

from odoo.addons.base.tests.common import HttpCase
from odoo.tests.common import tagged
from odoo.tests.common import users

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
        self.start_tour('/', 'time_off_request_calendar_view', login='enguerran')

        last_leave = self.env['hr.leave'].search([('employee_id.id', '=', self.employee_emp.id)]).sorted(lambda leave: leave.create_date)[-1]
        self.assertEqual(last_leave.date_from.weekday(), 3, "It should be Thursday")
        self.assertEqual(last_leave.date_from.hour, expected_leave_start, "Wrong start of the day")
        self.assertEqual(last_leave.date_to.hour, expected_leave_end, "Wrong end of the day")

    def test_timezone_calendar_event_single_day(self):
        """
        Test that single-day time off requests have a single day display in calendar
        """

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'requires_allocation': 'no',
            'leave_validation_type': 'no_validation',
            'create_calendar_meeting': True,
        })

        # case 1: full day in Los/Angeles tz

        test_date = date(2025, 4, 22)
        self.employee_emp.user_id.tz = 'America/Los_Angeles'
        self.employee_emp.resource_calendar_id.tz = 'America/Los_Angeles'
        leave = self.env['hr.leave'].create({
            'name': 'Single Day Leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': test_date,
            'request_date_to': test_date,
            'request_unit_half': False,
        })

        leave.action_validate()

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
            'holiday_status_id': leave_type.id,
            'request_date_from': test_date_half,
            'request_date_to': test_date_half,
            'request_unit_half': True,
            'request_date_from_period': 'pm',
        })

        leave_half.action_validate()

        self.assertEqual(leave_half.meeting_id.allday, False)
        self.assertEqual(leave_half.meeting_id.start, leave_half.date_from)
        self.assertEqual(leave_half.meeting_id.stop, leave_half.date_to)
