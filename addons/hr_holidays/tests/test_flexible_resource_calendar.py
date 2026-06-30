# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz
from datetime import datetime, date

from odoo.tests.common import TransactionCase

UTC = pytz.timezone('UTC')


class TestFlexibleResourceCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_40h_flex = cls.env['resource.calendar'].create({
            'name': 'Flexible 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'flexible_hours': True,
        })
        cls.flex_resource, cls.fully_flex_resource = cls.env['resource.resource'].create([{
            'name': 'Flex',
            'tz': 'UTC',
            'calendar_id': cls.calendar_40h_flex.id,
        }, {
            'name': 'fully flex',
            'tz': 'UTC',
            'calendar_id': False,
        }])

        cls.flex_employee, cls.fully_flex_employee = cls.env['hr.employee'].create([{
            'name': "flexible employee",
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'wage': 10,
            'resource_calendar_id': cls.calendar_40h_flex.id,
            'resource_id': cls.flex_resource.id,
        }, {
            'name': "fully flexible employee",
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'wage': 10,
            'resource_calendar_id': False,
            'resource_id': cls.fully_flex_resource.id,
        }])

    def test_flexible_resource_work_intervals_with_leaves(self):
        self.env['resource.calendar.leaves'].create([{
            'resource_id': self.flex_resource.id,
            'date_from': datetime(2025, 7, 31, 8),
            'date_to': datetime(2025, 8, 1, 17),
        }, {
            'resource_id': self.fully_flex_resource.id,
            'date_from': datetime(2025, 7, 31, 8),
            'date_to': datetime(2025, 8, 1, 17),
        }])

        custom_leave, half_day_leave = self.env['hr.leave.type'].create([{
            'name': 'Custom Leave',
            'requires_allocation': False,
            'request_unit': 'hour',
        }, {
            'name': 'Half day',
            'requires_allocation': False,
            'request_unit': 'half_day',
        }])

        self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True).create([{
            'name': 'Half 1',
            'holiday_status_id': half_day_leave.id,
            'employee_id': self.flex_employee.id,
            'request_date_from': date(2025, 7, 28),
            'request_date_to': date(2025, 7, 28),
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
        }, {
            'name': 'Half 2',
            'holiday_status_id': half_day_leave.id,
            'employee_id': self.flex_employee.id,
            'request_date_from': date(2025, 7, 30),
            'request_date_to': date(2025, 7, 30),
            'request_date_from_period': 'pm',
            'request_date_to_period': 'pm',
        }, {
            'name': 'Custom',
            'holiday_status_id': custom_leave.id,
            'employee_id': self.flex_employee.id,
            'request_date_from': date(2025, 7, 29),
            'request_date_to': date(2025, 7, 29),
            'request_hour_from': 11.0,
            'request_hour_to': 16.0,
        }, {
            'name': 'Half 1',
            'holiday_status_id': half_day_leave.id,
            'employee_id': self.fully_flex_employee.id,
            'request_date_from': date(2025, 7, 28),
            'request_date_to': date(2025, 7, 28),
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
        }, {
            'name': 'Half 2',
            'holiday_status_id': half_day_leave.id,
            'employee_id': self.fully_flex_employee.id,
            'request_date_from': date(2025, 7, 30),
            'request_date_to': date(2025, 7, 30),
            'request_date_from_period': 'pm',
            'request_date_to_period': 'pm',
        }, {
            'name': 'Custom',
            'holiday_status_id': custom_leave.id,
            'employee_id': self.fully_flex_employee.id,
            'request_date_from': date(2025, 7, 29),
            'request_date_to': date(2025, 7, 29),
            'request_hour_from': 11.0,
            'request_hour_to': 16.0,
        }]).action_approve()

        start_dt = datetime(2025, 7, 28).astimezone(UTC)
        end_dt = datetime(2025, 8, 3, 17).astimezone(UTC)

        resources = self.flex_resource | self.fully_flex_resource
        work_intervals, hours_per_day, hours_per_week = resources._get_flexible_resource_valid_work_intervals(start_dt, end_dt)

        self.maxDiff = None
        for resource in resources:
            self.assertEqual(work_intervals[resource.id]._items, [
                (datetime(2025, 7, 28, 12, 0, tzinfo=UTC), datetime(2025, 7, 28, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 7, 29, 0, 0, tzinfo=UTC), datetime(2025, 7, 29, 11, 0, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 7, 29, 16, 0, tzinfo=UTC), datetime(2025, 7, 29, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 7, 30, 0, 0, tzinfo=UTC), datetime(2025, 7, 30, 12, 0, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 2, 0, 0, tzinfo=UTC), datetime(2025, 8, 2, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 3, 0, 0, tzinfo=UTC), datetime(2025, 8, 3, 17, 0, tzinfo=UTC), self.env['resource.calendar.attendance']),
            ], "resource not available on 29, 31, 01, 28 morning and 30 afternoon. for other days, resource can do his hours at any moment of the day (from 00:00:00 to 23:59:59)")

        self.assertDictEqual(hours_per_day[self.flex_resource.id], {
            date(2025, 7, 28): 4.0,
            date(2025, 7, 29): 3.0,
            date(2025, 7, 30): 4.0,
            date(2025, 7, 31): 0.0,
            date(2025, 8, 1): 0.0,
            date(2025, 8, 2): 8.0,
            date(2025, 8, 3): 8.0,
        }, "hours_per_day/2 for half days off, and hours_per_day - number_of_hoursfor custom time off")
        self.assertTrue(self.fully_flex_resource.id not in hours_per_day)

        self.assertDictEqual(hours_per_week[self.flex_resource.id], {
            (2025, 31): 11.0,
            (2025, 32): 40.0,
        }, "week 31 (27/07 -> 02/08): 2 days off 31 & 01 (-16 hours), half day on 28 and 30 (-8 hours), 5 hours off on day 29 / hours = 40-(16+8+5) = 11 hours, no timeoff on week 32")
        self.assertTrue(self.fully_flex_resource.id not in hours_per_week)
