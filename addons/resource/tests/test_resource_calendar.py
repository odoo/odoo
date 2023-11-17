# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, common
from datetime import datetime, date

@tagged('post_install', '-at_install')
class TestResourceCalender(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.resource_calendar = cls.env['resource.calendar'].create({
            'name': 'resource calendar',
            'tz': 'UTC',
        })

        monday_morning_attendance = cls.env['resource.calendar.attendance'].create({
            'name': 'Monday Morning',
            'dayofweek': '0',
            'hour_from': 8.0,
            'hour_to': 12.0,
            'day_period': 'morning',
            'calendar_id': cls.resource_calendar.id,
        })
        monday_afternoon_attendance = cls.env['resource.calendar.attendance'].create({
            'name': 'Monday Afternoon',
            'dayofweek': '0',
            'hour_from': 12.0,
            'hour_to': 16.0,
            'day_period': 'afternoon',
            'calendar_id': cls.resource_calendar.id,
        })

        tuesday_morning_attendance = cls.resource_calendar.env['resource.calendar.attendance'].create({
            'name': 'Tuesday Morning',
            'dayofweek': '1',
            'date_from': date(2023, 1, 3),
            'date_to': date(2023, 1, 3),
            'hour_from': 8.0,
            'hour_to': 16.0,
            'day_period': 'morning',
            'calendar_id': cls.resource_calendar.id,
        })

        cls.resource_calendar.attendance_ids = [monday_morning_attendance.id, monday_afternoon_attendance.id, tuesday_morning_attendance.id]

    def test_get_work_duration_data(self):
        # test
        from_datetime = datetime(2023, 1, 2, 0, 0)
        to_datetime = datetime(2023, 1, 4, 0, 0)
        actual = self.resource_calendar.get_work_duration_data(
            from_datetime, to_datetime, compute_leaves=True, domain=None
        )

        # assert
        expected = {'days': 2.0, 'hours': 16.0}
        self.assertEqual(actual, expected)
