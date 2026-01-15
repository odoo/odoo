# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz
from datetime import datetime, date

from odoo.tests.common import TransactionCase

UTC = pytz.timezone('UTC')


class TestFlexibleResourceCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.flex_calendar = cls.env['resource.calendar'].create({
            'name': 'Flexible 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'flexible_hours': True,
        })

        cls.fully_flex_resource, cls.flex_resource = cls.env['resource.resource'].create([{
            'name': 'Wade Wilson',
            'calendar_id': False,
            'tz': 'UTC',
        }, {
            'name': 'Wade Wilson',
            'calendar_id': cls.flex_calendar.id,
            'tz': 'UTC',
        }])

        cls.env['resource.calendar.leaves'].create([
            {
                'resource_id': cls.flex_resource.id,
                'date_from': datetime(2025, 7, 29, 8),
                'date_to': datetime(2025, 7, 29, 17),
            },
            {
                'resource_id': cls.flex_resource.id,
                'date_from': datetime(2025, 7, 31, 8),
                'date_to': datetime(2025, 8, 1, 17),
            },
            {
                'resource_id': cls.fully_flex_resource.id,
                'date_from': datetime(2025, 7, 29, 8),
                'date_to': datetime(2025, 7, 29, 17),
            },
            {
                'resource_id': cls.fully_flex_resource.id,
                'date_from': datetime(2025, 7, 31, 8),
                'date_to': datetime(2025, 8, 1, 17),
            },
            {
                'calendar_id': cls.flex_calendar.id,
                'date_from': datetime(2025, 8, 4, 8),
                'date_to': datetime(2025, 8, 4, 17),
            },
            {
                'calendar_id': False,
                'date_from': datetime(2025, 8, 5, 8),
                'date_to': datetime(2025, 8, 5, 17),
            },
        ])

        cls.resources = cls.flex_resource | cls.fully_flex_resource

    def test_flexible_resource_work_intervals(self):
        start_dt = datetime(2025, 7, 28).astimezone(UTC)
        end_dt = datetime(2025, 8, 3, 17, 0).astimezone(UTC)

        work_intervals, hours_per_day, hours_per_week = self.resources._get_flexible_resource_valid_work_intervals(start_dt, end_dt)

        self.maxDiff = None
        for resource in self.resources:
            self.assertEqual(work_intervals[resource.id]._items, [
                (datetime(2025, 7, 28, 0, 0, tzinfo=UTC), datetime(2025, 7, 28, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 7, 30, 0, 0, tzinfo=UTC), datetime(2025, 7, 30, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 2, 0, 0, tzinfo=UTC), datetime(2025, 8, 2, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
                (datetime(2025, 8, 3, 0, 0, tzinfo=UTC), datetime(2025, 8, 3, 17, tzinfo=UTC), self.env['resource.calendar.attendance']),
            ], "resource not available on 29, 31 and 01, for other days, resource can do his hours at any moment of the day (from 00:00:00 to 23:59:59)")

        self.assertDictEqual(hours_per_day[self.flex_resource.id], {
            date(2025, 7, 28): 8.0,
            date(2025, 7, 29): 0.0,
            date(2025, 7, 30): 8.0,
            date(2025, 7, 31): 0.0,
            date(2025, 8, 1): 0.0,
            date(2025, 8, 2): 8.0,
            date(2025, 8, 3): 8.0,
        }, "0 hours when the resource is not available, hours_per_day from the calendar for working days")
        self.assertDictEqual(hours_per_week[self.flex_resource.id], {
            (2025, 31): 16.0,
            (2025, 32): 24.0,
        }, "3 days off (24 hours), remaining 16h, 2 days off (16 hours) for second week")

        self.assertTrue(self.fully_flex_resource.id not in hours_per_day and self.fully_flex_resource not in hours_per_week, "no daily and weekly limit")

        start_dt = datetime(2025, 8, 4).astimezone(UTC)
        end_dt = datetime(2025, 8, 5, 17, 0).astimezone(UTC)

        work_intervals, hours_per_day, hours_per_week = self.resources._get_flexible_resource_valid_work_intervals(start_dt, end_dt)

        self.assertEqual(work_intervals[self.flex_resource.id]._items, [], "flex calendar have a public holidays on day 4, and there's a public holiday on day 5 for all calendars")

        self.assertEqual(work_intervals[self.fully_flex_resource.id]._items, [
            (datetime(2025, 8, 4, 0, 0, tzinfo=UTC), datetime(2025, 8, 4, 23, 59, 59, 999999, tzinfo=UTC), self.env['resource.calendar.attendance']),
        ], "fully flex resource doesn't have a calendar, he should not follow the flex calendar public holiday, he follows holidays without a calendar")

    def test_hours_per_week_for_different_years(self):
        start_dt = datetime(2025, 12, 26).astimezone(UTC)
        end_dt = datetime(2026, 1, 1, 17).astimezone(UTC)

        _, _, hours_per_week = self.resources._get_flexible_resource_valid_work_intervals(start_dt, end_dt)
        self.assertDictEqual(hours_per_week[self.flex_resource.id], {
            (2025, 52): 40.0,
            (2026, 1): 40.0,
        }, "weeks are well computed when ")
