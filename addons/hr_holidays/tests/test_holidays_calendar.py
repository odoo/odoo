# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

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

    @users('bastien')
    def test_timeoff_calendar_resize_leave_duration(self):
        """Test resizing a leave to adjust its duration in the calendar view."""
        self.employee_hrmanager.tz = 'UTC'
        self.env.user.tz = 'UTC'
        hours_leave_type = self.env['hr.work.entry.type'].create(
            {'name': 'Hours Leave', 'requires_allocation': False, 'request_unit': 'hour', 'code': 'HOUR100'},
        )
        today = date.today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        hourly_leave = self.env['hr.leave'].create(
            {
                'name': 'Hourly Leave',
                'employee_id': self.employee_hrmanager.id,
                'work_entry_type_id': hours_leave_type.id,
                'request_date_from': sunday,
                'request_date_to': sunday,
                'request_hour_from': 8,
                'request_hour_to': 12,
            },
        )

        # Resize the leave to end at 14:00
        self.start_tour('/odoo', 'timeoff_calendar_resize_leave_duration_tour', login='bastien')

        assert hourly_leave.request_date_from == sunday
        assert hourly_leave.request_date_to == sunday
        assert hourly_leave.request_hour_from == 8
        assert hourly_leave.request_hour_to == 14

    @users('bastien')
    def test_timeoff_calendar_move_leave_to_next_day(self):
        """Test dragging and dropping leaves to reschedule them in the calendar view."""
        self.employee_hrmanager.tz = 'UTC'
        self.env.user.tz = 'UTC'
        leave_type = self.env['hr.work.entry.type'].create(
            {'name': 'Full Day Leave', 'requires_allocation': False, 'request_unit': 'day', 'code': 'DAY100'},
        )
        today = date.today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        tuesday = sunday + timedelta(days=2)
        thursday = sunday + timedelta(days=4)

        confirmed_leave, approved_leave, refused_leave = self.env['hr.leave'].create([
            {
                'name': 'Sunday Leave',
                'employee_id': self.employee_hrmanager.id,
                'work_entry_type_id': leave_type.id,
                'request_date_from': sunday,
                'request_date_to': sunday,
            },
            {
                'name': 'Tuesday Leave',
                'employee_id': self.employee_hrmanager.id,
                'work_entry_type_id': leave_type.id,
                'request_date_from': tuesday,
                'request_date_to': tuesday,
            },
            {
                'name': 'Thursday Leave',
                'employee_id': self.employee_hrmanager.id,
                'work_entry_type_id': leave_type.id,
                'request_date_from': thursday,
                'request_date_to': thursday,
            },
        ])
        approved_leave.action_approve()
        refused_leave.action_refuse()

        # Moving all leaves to the next day
        self.start_tour('/odoo', 'timeoff_calendar_move_leave_to_next_day_tour', login='bastien')

        assert confirmed_leave.request_date_from == sunday + timedelta(days=1)
        assert confirmed_leave.request_date_to == sunday + timedelta(days=1)
        assert approved_leave.request_date_from == tuesday
        assert approved_leave.request_date_to == tuesday
        assert refused_leave.request_date_from == thursday
        assert refused_leave.request_date_to == thursday
