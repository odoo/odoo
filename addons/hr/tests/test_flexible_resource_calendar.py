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

    def test_flexible_resource_work_intervals_with_contracts(self):
        flex_employee, fully_flex_employee = self.env['hr.employee'].create([{
            'name': "flex employee",
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'contract_date_end': date(2025, 7, 29),
            'wage': 10,
            'resource_calendar_id': self.calendar_40h_flex.id,
            'resource_id': self.flex_resource.id,
        }, {
            'name': "fully flex employee",
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'contract_date_end': date(2025, 7, 29),
            'wage': 10,
            'resource_calendar_id': False,
            'resource_id': self.fully_flex_resource.id,
        }])
        flex_employee.create_version({
            'date_version': date(2025, 8, 2),
            'contract_date_start': date(2025, 8, 2),
            'wage': 10,
            'resource_calendar_id': self.calendar_40h_flex.id,
        })

        fully_flex_employee.create_version({
            'date_version': date(2025, 8, 2),
            'contract_date_start': date(2025, 8, 2),
            'wage': 10,
            'resource_calendar_id': False,
        })

        start_dt = datetime(2025, 7, 28).astimezone(UTC)
        end_dt = datetime(2025, 8, 3, 17).astimezone(UTC)

        resources = self.flex_resource | self.fully_flex_resource
        work_intervals, hours_per_day, hours_per_week = resources._get_flexible_resource_valid_work_intervals(start_dt, end_dt)
        self.maxDiff = None
        for resource in resources:
            self.assertEqual(work_intervals[resource.id]._items, [
                (datetime(2025, 7, 28, 0, 0, tzinfo=UTC), datetime(2025, 7, 28, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 7, 29, 0, 0, tzinfo=UTC), datetime(2025, 7, 29, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 2, 0, 0, tzinfo=UTC), datetime(2025, 8, 2, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 3, 0, 0, tzinfo=UTC), datetime(2025, 8, 3, 17, 0, tzinfo=UTC), self.env['resource.calendar.attendance']),
            ], "work intervals should be inside contract 1 and 2 periods, no contracts on 30, 31, 1")

        self.assertDictEqual(hours_per_day[self.flex_resource.id], {
            date(2025, 7, 28): 8.0,
            date(2025, 7, 29): 8.0,
            date(2025, 8, 2): 8.0,
            date(2025, 8, 3): 8.0,
        })

        self.assertDictEqual(hours_per_week[self.flex_resource.id], {
            (2025, 31): 32.0,
            (2025, 32): 40.0,
        }, "working day 27, 28, 29 and 02 on week 31, having a valid contract on week 32")

        self.assertTrue(self.fully_flex_resource.id not in hours_per_day, "no date hours limit for fully flexible employees")

    def test_flexible_resource_work_intervals_without_contracts(self):
        start_dt = datetime(2025, 7, 28).astimezone(UTC)
        end_dt = datetime(2025, 8, 3, 17).astimezone(UTC)

        resources = self.flex_resource | self.fully_flex_resource
        work_intervals, hours_per_day, hours_per_week = resources._get_flexible_resource_valid_work_intervals(start_dt, end_dt)
        self.maxDiff = None
        for resource in resources:
            self.assertEqual(work_intervals[resource.id]._items, [
                (datetime(2025, 7, 28, 0, 0, tzinfo=UTC), datetime(2025, 7, 28, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 7, 29, 0, 0, tzinfo=UTC), datetime(2025, 7, 29, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 7, 30, 0, 0, tzinfo=UTC), datetime(2025, 7, 30, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 7, 31, 0, 0, tzinfo=UTC), datetime(2025, 7, 31, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 1, 0, 0, tzinfo=UTC), datetime(2025, 8, 1, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 2, 0, 0, tzinfo=UTC), datetime(2025, 8, 2, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 3, 0, 0, tzinfo=UTC), datetime(2025, 8, 3, 17, 0, tzinfo=UTC), self.env['resource.calendar.attendance']),
            ], "when no contracts at all, we get the full period")

        self.assertDictEqual(hours_per_day[self.flex_resource.id], {
            date(2025, 7, 28): 8.0,
            date(2025, 7, 29): 8.0,
            date(2025, 7, 30): 8.0,
            date(2025, 7, 31): 8.0,
            date(2025, 8, 1): 8.0,
            date(2025, 8, 2): 8.0,
            date(2025, 8, 3): 8.0,
        }, "when no contracts at all, we get the full period")
        self.assertTrue(self.fully_flex_resource.id not in hours_per_day, "no date hours limit for fully flexible employees")

        self.assertDictEqual(hours_per_week[self.flex_resource.id], {
            (2025, 31): 40.0,
            (2025, 32): 40.0,
        })
