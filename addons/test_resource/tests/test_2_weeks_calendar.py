# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from zoneinfo import ZoneInfo

from odoo.tests.common import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class Test2WeeksCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Week 1: 16 Hours - Week 2: 30 Hours
        cls.two_weeks_cal_fixed = cls.env['resource.calendar'].create([
            {
                "name": "2-weeks calendar",
                "two_weeks_calendar": True,
                "attendance_ids": [(
                    0, 0, {
                        "hour_from": att[0],
                        "hour_to": att[1],
                        "dayofweek": str(att[2]),
                        "week_type": att[3],
                    },
                ) for att in [
                    (8, 16, 0, "0"),
                    (9, 17, 1, "0"),
                    (8, 16, 0, "1"),
                    (7, 15, 2, "1"),
                    (8, 16, 3, "1"),
                    (10, 16, 4, "1"),
                ]],
            },
        ])

        # Week 1: 16 Hours - Week 2: 30 Hours
        cls.two_weeks_cal_duration = cls.env['resource.calendar'].create([
            {
                "name": "2-weeks calendar",
                "two_weeks_calendar": True,
                "attendance_ids": [(
                    0, 0, {
                        "duration_hours": att[0],
                        "dayofweek": str(att[1]),
                        "week_type": att[2],
                    },
                ) for att in [
                    (8, 0, "0"),
                    (8, 1, "0"),
                    (8, 0, "1"),
                    (8, 2, "1"),
                    (8, 3, "1"),
                    (6, 4, "1"),
                ]],
            },
        ])

        cls.jules, cls.aaron = cls.env["resource.test"].create([
            {
                "name": "Jules",
                'tz': 'UTC',
                "resource_calendar_id": cls.two_weeks_cal_fixed.id,
            },
            {
                "name": "Aaron",
                'tz': 'Asia/Singapore',  # UTC +8
                "resource_calendar_id": cls.two_weeks_cal_duration.id,
            },
        ])

    def test_2_weeks_fixed(self):
        jules_tz = ZoneInfo(self.jules.tz)
        # 2 weeks calendar week 1
        hours = self.two_weeks_cal_fixed.get_work_hours_count(
            datetime(2018, 4, 2, 0, 0, 0, tzinfo=jules_tz),
            datetime(2018, 4, 6, 23, 59, 59, tzinfo=jules_tz),
        )
        self.assertEqual(hours, 30)

        # 2 weeks calendar week 1
        hours = self.two_weeks_cal_fixed.get_work_hours_count(
            datetime(2018, 4, 16, 0, 0, 0, tzinfo=jules_tz),
            datetime(2018, 4, 20, 23, 59, 59, tzinfo=jules_tz),
        )
        self.assertEqual(hours, 30)

        # 2 weeks calendar week 2
        hours = self.two_weeks_cal_fixed.get_work_hours_count(
            datetime(2018, 4, 9, 0, 0, 0, tzinfo=jules_tz),
            datetime(2018, 4, 13, 23, 59, 59, tzinfo=jules_tz),
        )
        self.assertEqual(hours, 16)

        # 2 weeks calendar week 2, leave during a day where he doesn't work this week
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'Time Off Jules week 2',
            'calendar_id': self.two_weeks_cal_fixed.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 11, 4, 0, 0),
            'date_to': datetime(2018, 4, 13, 4, 0, 0),
        })

        hours = self.two_weeks_cal_fixed.get_work_hours_count(
            datetime(2018, 4, 9, 0, 0, 0, tzinfo=jules_tz),
            datetime(2018, 4, 13, 23, 59, 59, tzinfo=jules_tz),
        )
        self.assertEqual(hours, 16)

        leave.unlink()

        # 2 weeks calendar week 2, leave during a day where he works this week
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'Time Off Jules week 2',
            'calendar_id': self.two_weeks_cal_fixed.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 9, 0, 0, 0),
            'date_to': datetime(2018, 4, 9, 23, 59, 0),
        })

        hours = self.two_weeks_cal_fixed.get_work_hours_count(
            datetime(2018, 4, 9, 0, 0, 0, tzinfo=jules_tz),
            datetime(2018, 4, 13, 23, 59, 59, tzinfo=jules_tz),
        )
        self.assertEqual(hours, 8)

        leave.unlink()

    def test_2_weeks_duration(self):
        aaron_tz = ZoneInfo(self.aaron.tz)
        # 2 weeks calendar week 1
        hours = self.two_weeks_cal_duration.get_work_hours_count(
            datetime(2018, 4, 2, 0, 0, 0, tzinfo=aaron_tz),
            datetime(2018, 4, 6, 23, 59, 59, tzinfo=aaron_tz),
        )
        self.assertEqual(hours, 30)

        # 2 weeks calendar week 1
        hours = self.two_weeks_cal_duration.get_work_hours_count(
            datetime(2018, 4, 16, 0, 0, 0, tzinfo=aaron_tz),
            datetime(2018, 4, 20, 23, 59, 59, tzinfo=aaron_tz),
        )
        self.assertEqual(hours, 30)

        # 2 weeks calendar week 2
        hours = self.two_weeks_cal_duration.get_work_hours_count(
            datetime(2018, 4, 9, 0, 0, 0, tzinfo=aaron_tz),
            datetime(2018, 4, 13, 23, 59, 59, tzinfo=aaron_tz),
        )
        self.assertEqual(hours, 16)

        # 2 weeks calendar week 2, leave during a day where he doesn't work this week
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'Time Off Jules week 2',
            'calendar_id': self.two_weeks_cal_duration.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 11, 0, 0, 0),
            'date_to': datetime(2018, 4, 13, 0, 0, 0),
        })

        hours = self.two_weeks_cal_duration.get_work_hours_count(
            datetime(2018, 4, 9, 0, 0, 0, tzinfo=aaron_tz),
            datetime(2018, 4, 13, 23, 59, 59, tzinfo=aaron_tz),
        )
        self.assertEqual(hours, 16)

        leave.unlink()

        # 2 weeks calendar week 2, leave during a day where he works this week
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'Time Off Jules week 2',
            'calendar_id': self.two_weeks_cal_duration.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 8, 16, 0, 0),
            'date_to': datetime(2018, 4, 9, 15, 59, 0),
        })

        hours = self.two_weeks_cal_duration.get_work_hours_count(
            datetime(2018, 4, 9, 0, 0, 0, tzinfo=aaron_tz),
            datetime(2018, 4, 13, 23, 59, 59, tzinfo=aaron_tz),
        )
        self.assertEqual(hours, 8)

        leave.unlink()

    def test_compute_work_time_rate_with_two_weeks_calendar(self):
        """Test Case: check if the computation of the work time rate in the resource.calendar is correct."""
        def create_attendance_ids(attendance_list):
            return [(0, 0, {'week_type': str(i), **attendance}) for i in range(0, 2) for attendance in attendance_list]

        attendance_list = [
            {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
        ]

        # Define a mid time
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Calendar Mid-Time',
            'two_weeks_calendar': True,
            'full_time_required_hours': 40,
            'attendance_ids': create_attendance_ids(attendance_list),
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 50, 2)

        attendance_list = [
            {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
        ]

        # Define a 4/5
        resource_calendar.write({
            'name': 'Calendar (4 / 5)',
            'attendance_ids': create_attendance_ids(attendance_list),
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 80, 2)

        # Define a 9/10
        resource_calendar.write({
            'name': 'Calendar (9 / 10)',
            'attendance_ids': create_attendance_ids([
                {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            ]),
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 90, 2)

    def test_empty_working_hours_for_two_weeks_resource(self):
        calendar = self.env['resource.calendar'].create([
            {
                "name": "2-weeks calendar",
                "two_weeks_calendar": True,
                "attendance_ids": [],
            },
        ])

        self.env['resource.calendar.attendance'].create({
            'calendar_id': calendar.id,
            'hour_from': 0,
            'hour_to': 0,
        })
        resource_hour = calendar._get_hours_per_day()
        self.assertEqual(resource_hour, 0.0)

        self.env['resource.calendar.attendance'].create({
            'calendar_id': calendar.id,
            'duration_hours': 0,
        })
        resource_hour = calendar._get_hours_per_day()
        self.assertEqual(resource_hour, 0.0)

    def test_work_data_2_weeks(self):
        jules_tz = ZoneInfo(self.jules.tz)
        # Jules with 2 weeks calendar
        # 02-04-2018 00:00:00 - 6-04-2018 23:59:59
        data = self.jules._get_work_days_data_batch(
            datetime(2018, 4, 2, 0, 0, 0, tzinfo=jules_tz),
            datetime(2018, 4, 6, 23, 59, 59, tzinfo=jules_tz),
        )[self.jules.id]
        self.assertEqual(data, {'days': 4, 'hours': 30})

        # Jules with 2 weeks calendar
        # 02-04-2018 00:00:00 - 14-04-2018 23:59:59
        data = self.jules._get_work_days_data_batch(
            datetime(2018, 4, 2, 0, 0, 0, tzinfo=jules_tz),
            datetime(2018, 4, 14, 23, 59, 59, tzinfo=jules_tz),
        )[self.jules.id]
        self.assertEqual(data, {'days': 6, 'hours': 46})

        # Jules with 2 weeks calendar
        # 12-29-2014 00:00:00 - 27-12-2019 23:59:59 => 261 weeks
        # 130 weeks type 1: 131*4 = 524 days and 131*30 = 3930 hours
        # 131 weeks type 2: 130*2 = 260 days and 130*16 = 2080 hours
        data = self.jules._get_work_days_data_batch(
            datetime(2014, 12, 29, 0, 0, 0, tzinfo=jules_tz),
            datetime(2019, 12, 27, 23, 59, 59, tzinfo=jules_tz),
        )[self.jules.id]
        self.assertEqual(data, {'days': 784, 'hours': 6010})
