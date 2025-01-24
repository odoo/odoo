# -*- coding: utf-8 -*-
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

    def test_search_holidays_calendar(self):
        """
        Test the search functionality of the holidays calendar.

        Verifies that the search results match expected outcomes for different
        search terms and user roles, considering user access rights.
        """
        david = self.employee_emp
        holiday_status_sick = self.env.ref('hr_holidays.holiday_status_sl')
        holiday_status_3_days = self.env.ref('hr_holidays.holiday_status_cl')

        this_monday = date.today() - timedelta(days=date.today().weekday())
        next_monday = this_monday + timedelta(weeks=1)
        leaves = self.env['hr.leave'].create([{
            'name': '3 days Off',
            'employee_id': david.id,
            'holiday_status_id': holiday_status_3_days.id,
            'request_date_from': this_monday,
            'request_date_to': this_monday + timedelta(days=2),
        }, {
            'name': 'Sick Ronnie',
            'employee_id': david.id,
            'holiday_status_id': holiday_status_sick.id,
            'request_date_from': next_monday,
            'request_date_to': next_monday + timedelta(days=4),
        }])

        search_cases = [
            ('3 days', [leaves[0], leaves[0], leaves[0]]),
            ('Sick', [leaves.browse(), leaves[1], leaves[1]]),
            ('David', [leaves, leaves, leaves]),
        ]
        users = [self.user_employee, self.user_hrmanager, self.user_hruser]

        for term, expected_results in search_cases:
            for user, expected in zip(users, expected_results):
                records = self.env['hr.leave.report.calendar'].search(expression.AND([
                    [('leave_id', 'in', leaves.ids)],
                    self.env['hr.leave.report.calendar'].with_user(user)._search_name('ilike', term),
                ]))
                self.assertEqual(
                    records.leave_id, 
                    expected, 
                    f"Failed for term '{term}' with user {user.login}. Expected {expected}, got {records}."
                )
