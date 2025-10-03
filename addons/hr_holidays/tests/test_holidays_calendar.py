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
        self.start_tour('/', 'time_off_request_calendar_view', login='enguerran')

        last_leave = self.env['hr.leave'].search([('employee_id.id', '=', self.employee_emp.id)]).sorted(lambda leave: leave.create_date)[-1]
        self.assertEqual(last_leave.date_from.weekday(), 3, "It should be Thursday")
        self.assertEqual(last_leave.date_from.hour, expected_leave_start, "Wrong start of the day")
        self.assertEqual(last_leave.date_to.hour, expected_leave_end, "Wrong end of the day")

    @users('bastien')
    def test_timeoff_calendar_resize_leave_duration(self):
        """Test resizing a leave to adjust its duration in the calendar view."""
        self.employee_hrmanager.tz = 'UTC'
        self.env.user.tz = 'UTC'
        hours_leave_type = self.env['hr.leave.type'].create(
            {'name': 'Hours Leave', 'requires_allocation': False, 'request_unit': 'hour'},
        )
        today = date.today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        hourly_leave = self.env['hr.leave'].create(
            {
                'name': 'Hourly Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': hours_leave_type.id,
                'request_date_from': sunday,
                'request_date_to': sunday,
                'request_hour_from': 8,
                'request_hour_to': 12,
            },
        )

        # Resize the leave to end at 14:00
        self.start_tour('/', 'timeoff_calendar_resize_leave_duration_tour', login='bastien')

        assert hourly_leave.request_date_from == sunday
        assert hourly_leave.request_date_to == sunday
        assert hourly_leave.request_hour_from == 8
        assert hourly_leave.request_hour_to == 14

    @users('bastien')
    def test_timeoff_calendar_move_leave_to_next_day(self):
        """Test dragging and dropping leaves to reschedule them in the calendar view."""
        self.employee_hrmanager.tz = 'UTC'
        self.env.user.tz = 'UTC'
        leave_type = self.env['hr.leave.type'].create(
            {'name': 'Full Day Leave', 'requires_allocation': False, 'request_unit': 'day'},
        )
        today = date.today()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        tuesday = sunday + timedelta(days=2)
        thursday = sunday + timedelta(days=4)

        confirmed_leave, approved_leave, refused_leave = self.env['hr.leave'].create([
            {
                'name': 'Sunday Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': sunday,
                'request_date_to': sunday,
            },
            {
                'name': 'Tuesday Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': tuesday,
                'request_date_to': tuesday,
            },
            {
                'name': 'Thursday Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': thursday,
                'request_date_to': thursday,
            },
        ])
        approved_leave.action_approve()
        refused_leave.action_refuse()

        # Moving all leaves to the next day
        self.start_tour('/', 'timeoff_calendar_move_leave_to_next_day_tour', login='bastien')

        assert confirmed_leave.request_date_from == sunday + timedelta(days=1)
        assert confirmed_leave.request_date_to == sunday + timedelta(days=1)
        assert approved_leave.request_date_from == tuesday
        assert approved_leave.request_date_to == tuesday
        assert refused_leave.request_date_from == thursday
        assert refused_leave.request_date_to == thursday
