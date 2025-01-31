from pytz import utc
from datetime import date, datetime

from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestResourceCalendar(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})
        cls.calendar_fixed_40h = cls.env['resource.calendar'].create({
            'name': 'Fixed calendar',
            'schedule_type': 'fixed_time',
            'hours_per_day': 8,
            'monday': True,
            'tuesday': True,
            'wednesday': True,
            'thursday': True,
            'friday': True,
        })
        cls.calendar_fixed_with_hours = cls.env['resource.calendar'].create({
            'name': 'Fixed calendar with hours',
            'schedule_type': 'fixed_time',
            'fixed_time_with_hours': True,
            'monday': True,
            'tuesday': True,
            'wednesday': True,
            'thursday': True,
            'friday': True,
            'monday_hours': 10,
            'tuesday_hours': 10,
            'wednesday_hours': 8,
            'thursday_hours': 9,
            'friday_hours': 8,
        })

    def test_get_days_per_week(self):
        self.assertEqual(self.calendar_fixed_40h._get_days_per_week(), 5)

    def test_works_on_date(self):
        tets_date = date(2025, 1, 1)
        self.assertTrue(self.calendar_fixed_40h._works_on_date(tets_date))

    def test_get_max_number_of_hours(self):
        start = datetime.combine(date(2025, 1, 1), datetime.min.time())
        end = datetime.combine(date(2025, 1, 5), datetime.min.time())

        self.assertEqual(self.calendar_fixed_40h._get_max_number_of_hours(start, end), 8)
        self.assertEqual(self.calendar_fixed_with_hours._get_max_number_of_hours(start, end), 9)

    def test_attendance_intervals_batch(self):
        start = datetime.combine(date(2025, 1, 1), datetime.min.time(), tzinfo=utc)
        end = datetime.combine(date(2025, 1, 5), datetime.min.time(), tzinfo=utc)
        intervals = self.calendar_40h._attendance_intervals_batch(start, end)
        intervals_fixed = self.calendar_fixed_40h._attendance_intervals_batch(start, end)
        self.assertEqual(len(intervals[False]), 6)
        self.assertEqual(len(intervals_fixed[False]), 3)
