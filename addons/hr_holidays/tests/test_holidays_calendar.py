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
    def test_time_off_calendar_drag_and_resize_update_requests(self):
        """
        Test the drag&drop and resize of leaves in the calendar view.
        """
        self.employee_hrmanager.tz = 'UTC'
        self.env.user.tz = 'UTC'
        full_day_leave_type, half_day_leave_type, hours_leave_type = self.env['hr.leave.type'].create([
            {'name': 'Full Day Leave', 'requires_allocation': False, 'request_unit': 'day'},
            {'name': 'Half Day Leave', 'requires_allocation': False, 'request_unit': 'half_day'},
            {'name': 'Hours Leave', 'requires_allocation': False, 'request_unit': 'hour'},
        ])
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday - timedelta(days=1)
        tuesday = sunday + timedelta(days=2)
        thursday = sunday + timedelta(days=4)

        hourly_leave, full_day_leave, half_day_leave = self.env['hr.leave'].create([
            {
                'name': 'Hourly Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': hours_leave_type.id,
                'request_date_from': sunday,
                'request_date_to': sunday,
                'request_hour_from': 8,
                'request_hour_to': 12,
            },
            {
                'name': 'Full Day Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': full_day_leave_type.id,
                'request_date_from': tuesday,
                'request_date_to': tuesday,
            },
            {
                'name': 'Half Day Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': half_day_leave_type.id,
                'request_date_from': thursday,
                'request_date_to': thursday,
                'request_date_from_period': 'am',
                'request_date_to_period': 'am',
            }
        ])

        # Resize tour will increase the duration of the hourly leave(on sunday) by 2 hours
        self.start_tour('/', 'timeoff_calendar_resize_tour', login='bastien')

        assert hourly_leave.request_date_from == sunday
        assert hourly_leave.request_date_to == sunday
        assert hourly_leave.request_hour_from == 8
        assert hourly_leave.request_hour_to == 14

        # Drag&drop tour will move all leaves to the next day
        self.start_tour('/', 'timeoff_calendar_drag_drop_tour', login='bastien')

        assert hourly_leave.request_date_from == sunday + timedelta(days=1)
        assert hourly_leave.request_date_to == sunday + timedelta(days=1)
        assert full_day_leave.request_date_from == tuesday + timedelta(days=1)
        assert full_day_leave.request_date_to == tuesday + timedelta(days=1)
        assert half_day_leave.request_date_from == thursday + timedelta(days=1)
        assert half_day_leave.request_date_to == thursday + timedelta(days=1)
