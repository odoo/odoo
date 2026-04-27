# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestResource(TransactionCase):

    def test_compute_work_time_rate_with_one_week_calendar(self):
        """Test Case: check if the computation of the work time rate in the resource.calendar is correct."""
        # Define a mid time
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Calendar Mid-Time',
            'hours_per_day': 8,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 40,
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})
            ]
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 50, 2)

        # Define a 4/5
        resource_calendar.write({
            'name': 'Calendar (4 / 5)',
            'attendance_ids': [
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ]
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 80, 2)

        # Define a 9/10
        resource_calendar.write({
            'name': 'Calendar (9 / 10)',
            'attendance_ids': [(0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})]
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 90, 2)

        # Define a Full-Time
        resource_calendar.write({
            'name': 'Calendar Full-Time',
            'attendance_ids': [(0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})]
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 100, 2)

    def test_compute_work_time_rate_with_two_weeks_calendar(self):
        """Test Case: check if the computation of the work time rate in the resource.calendar is correct."""
        create_attendance_ids = lambda attendance_list: [(0, 0, {'week_type': str(i), **attendance}) for i in range(0, 2) for attendance in attendance_list]
        attendance_list = [
            {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'},
            {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'},
            {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}
        ]

        # Define a mid time
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Calendar Mid-Time',
            'hours_per_day': 8,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': True,
            'hours_per_week': 40,
            'full_time_required_hours': 40,
            'attendance_ids': create_attendance_ids(attendance_list)
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 50, 2)

        attendance_list = [
            {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'},
            {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}
        ]

        # Define a 4/5
        resource_calendar.write({
            'name': 'Calendar (4 / 5)',
            'attendance_ids': create_attendance_ids(attendance_list)
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 80, 2)

        # Define a 9/10
        resource_calendar.write({
            'name': 'Calendar (9 / 10)',
            'attendance_ids': create_attendance_ids([{'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}])
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 90, 2)

        # Define a Full-Time
        resource_calendar.write({
            'name': 'Calendar Full-Time',
            'attendance_ids': create_attendance_ids([{'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}])
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 100, 2)

    def test_compute_work_time_rate_with_credit_time_in_calendar(self):
        """Test Case: check if the computation of the work rate time is correct event if the user add some credit time as attendances."""
        credit_time = self.env['hr.work.entry.type'].create({
            'name': 'Credit Time',
            'code': 'Leave',
            'is_leave': True
        })

        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Calendar Mid-Time',
            'hours_per_day': 8,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 40,
            'full_time_required_hours': 40,
            'attendance_ids': [(5, 0, 0)]
        })

        # Define a mid time
        attendances = self.env['resource.calendar.attendance'].create([
            {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'calendar_id': resource_calendar.id},
            {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch', 'calendar_id': resource_calendar.id},
            {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'calendar_id': resource_calendar.id},
            {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'calendar_id': resource_calendar.id},
            {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch', 'calendar_id': resource_calendar.id},
            {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'calendar_id': resource_calendar.id},
            {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'calendar_id': resource_calendar.id},
            {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch', 'calendar_id': resource_calendar.id},
            {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'work_entry_type_id': credit_time.id, 'calendar_id': resource_calendar.id},
            {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': credit_time.id, 'calendar_id': resource_calendar.id},
            {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch', 'calendar_id': resource_calendar.id},
            {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'work_entry_type_id': credit_time.id, 'calendar_id': resource_calendar.id},
            {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': credit_time.id, 'calendar_id': resource_calendar.id},
            {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch', 'calendar_id': resource_calendar.id},
            {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'work_entry_type_id': credit_time.id, 'calendar_id': resource_calendar.id}
        ])
        self.assertAlmostEqual(resource_calendar.work_time_rate, 50, 2)

        # Define a 4/5
        attendances_to_update = attendances.filtered(lambda attendance: (attendance.dayofweek == '2' and attendance.day_period == 'afternoon') or attendance.dayofweek == '3')
        resource_calendar.write({
            'name': 'Calendar (4 / 5)',
            'attendance_ids': [(1, attendance.id, {'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id}) for attendance in attendances_to_update]
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 80, 2)

        # Define a 9/10
        attendances_to_update = attendances.filtered(lambda attendance: attendance.dayofweek == '4' and attendance.day_period == 'morning')
        resource_calendar.write({
            'name': 'Calendar (9 / 10)',
            'attendance_ids': [(1, attendance.id, {'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id}) for attendance in attendances_to_update]
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 90, 2)

        # Define a Full-Time
        attendances_to_update = attendances.filtered(lambda attendance: attendance.dayofweek == '4' and attendance.day_period == 'afternoon')
        resource_calendar.write({
            'name': 'Calendar Full-Time',
            'attendance_ids': [(1, attendance.id, {'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id}) for attendance in attendances_to_update]
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 100, 2)
