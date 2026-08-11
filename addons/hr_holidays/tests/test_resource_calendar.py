# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, time
from pytz import timezone

from odoo import Command
from odoo.tests.common import tagged

from odoo.addons.hr_holidays.tests.common import TestHolidayContract


@tagged('post_install', '-at_install')
class TestResourceCalendar(TestHolidayContract):

    def test_time_off_half_day_duration(self):
        """if working schedule is of full day period, Duration should be correct"""

        new_calendar_40h = self.env['resource.calendar'].create({
            'name': '40h calendar new',
            'attendance_ids': [
                Command.create({
                    'name': 'Monday full day',
                    'dayofweek': '0',
                    'hour_from': 10,
                    'hour_to': 18,
                    'day_period': 'full_day',
                }),
                Command.create({
                    'name': 'Tuesday full day',
                    'dayofweek': '1',
                    'hour_from': 10,
                    'hour_to': 18,
                    'day_period': 'full_day',
                }),
            ],
        })
        self.jules_emp.version_id.resource_calendar_id = new_calendar_40h.id
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test half day type',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'request_unit': 'half_day',
        })

        leave_morning, leave_afternoon, leave_one_and_half = self.env['hr.leave'].create([
            {
                'name': 'Half Day Leave(morning)',
                'employee_id': self.jules_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date(2025, 4, 21),
                'request_date_to': date(2025, 4, 21),
                'request_date_from_period': 'am',
                'request_date_to_period': 'am',
            },
            {
                'name': 'Half Day Leave(afternoon)',
                'employee_id': self.jules_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date(2025, 4, 22),
                'request_date_to': date(2025, 4, 22),
                'request_date_from_period': 'pm',
                'request_date_to_period': 'pm',
            },
            {
                'name': 'One and half Day Leave',
                'employee_id': self.jules_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date(2025, 4, 14),
                'request_date_to': date(2025, 4, 15),
                'request_date_from_period': 'am',
                'request_date_to_period': 'am',
            },
        ])
        self.assertEqual(leave_morning.number_of_days, 0.5)
        self.assertEqual(leave_afternoon.number_of_days, 0.5)
        self.assertEqual(leave_one_and_half.number_of_days, 1.5)

    def test_time_off_half_day_duration_based_calendar(self):
        attendance_ids = []
        for dayofweek, day_name in [
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
        ]:
            attendance_ids += [
                Command.create({
                    'name': f'{day_name} Morning',
                    'dayofweek': dayofweek,
                    'duration_hours': 3.36,
                    'day_period': 'morning',
                }),
                Command.create({
                    'name': f'{day_name} Afternoon',
                    'dayofweek': dayofweek,
                    'duration_hours': 3.36,
                    'day_period': 'afternoon',
                }),
            ]

        calendar = self.env['resource.calendar'].create({
            'name': 'Duration based calendar',
            'duration_based': True,
            'attendance_ids': attendance_ids,
        })
        self.jules_emp.version_id.resource_calendar_id = calendar
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test duration based half day type',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'request_unit': 'half_day',
        })

        leave = self.env['hr.leave'].create({
            'name': 'Full week half day leave',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2026, 4, 20),
            'request_date_to': date(2026, 4, 24),
            'request_date_from_period': 'am',
            'request_date_to_period': 'pm',
        })

        self.assertEqual(leave.number_of_days, 5)

    def test_adjust_leaves_multiple_intervals(self):
        """_adjust_leaves must be able to combine several leave intervals.

        It uses `Intervals.__or__` (the `|` operator) to accumulate the adjusted
        intervals. Regression test for a case where `+=` was used instead, which
        raised a TypeError as soon as more than zero leaves had to be adjusted,
        since Intervals doesn't implement `__add__`/`__radd__`.
        """
        attendance_ids = []
        for dayofweek, day_name in [('0', 'Monday'), ('1', 'Tuesday')]:
            attendance_ids += [
                Command.create({
                    'name': f'{day_name} Morning',
                    'dayofweek': dayofweek,
                    'duration_hours': 3.36,
                    'day_period': 'morning',
                }),
                Command.create({
                    'name': f'{day_name} Afternoon',
                    'dayofweek': dayofweek,
                    'duration_hours': 3.36,
                    'day_period': 'afternoon',
                }),
            ]

        calendar = self.env['resource.calendar'].create({
            'name': 'Duration based calendar',
            'duration_based': True,
            'attendance_ids': attendance_ids,
        })
        self.jules_emp.version_id.resource_calendar_id = calendar
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test duration based half day type',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'request_unit': 'half_day',
        })

        self.env['hr.leave'].create([
            {
                'name': 'Monday morning leave',
                'employee_id': self.jules_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date(2026, 4, 20),
                'request_date_to': date(2026, 4, 20),
                'request_date_from_period': 'am',
                'request_date_to_period': 'am',
            },
            {
                'name': 'Tuesday afternoon leave',
                'employee_id': self.jules_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date(2026, 4, 21),
                'request_date_to': date(2026, 4, 21),
                'request_date_from_period': 'pm',
                'request_date_to_period': 'pm',
            },
        ])

        tz = timezone(self.jules_emp.resource_id.tz)
        start_dt = tz.localize(datetime.combine(date(2026, 4, 20), time.min))
        stop_dt = tz.localize(datetime.combine(date(2026, 4, 23), time.min))
        leave_intervals = calendar._leave_intervals_batch(
            start_dt, stop_dt, resources=self.jules_emp.resource_id,
        )[self.jules_emp.resource_id.id]
        # sanity check: both leaves were found and are two distinct (non-adjacent) intervals
        self.assertEqual(len(leave_intervals), 2)

        # This used to raise a TypeError before the fix, since `_adjust_leaves`
        # combined intervals with `+=` instead of `|=`.
        adjusted_leaves = self.jules_emp._adjust_leaves(leave_intervals)

        intervals = sorted(adjusted_leaves, key=lambda interval: interval[0])
        self.assertEqual(len(intervals), 2)

        monday_start, monday_stop, _ = intervals[0]
        self.assertEqual((monday_start.date(), monday_start.time()), (date(2026, 4, 20), time.min))
        self.assertEqual((monday_stop.date(), monday_stop.time()), (date(2026, 4, 20), time(12)))

        tuesday_start, tuesday_stop, _ = intervals[1]
        self.assertEqual((tuesday_start.date(), tuesday_start.time()), (date(2026, 4, 21), time(12)))
        self.assertEqual((tuesday_stop.date(), tuesday_stop.time()), (date(2026, 4, 22), time.min))
