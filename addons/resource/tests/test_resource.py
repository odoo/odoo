# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.dates

from datetime import datetime, timedelta, date, time

from dateutil import rrule
from dateutil.relativedelta import relativedelta

from odoo.fields import Date, Datetime
from odoo.addons.resource.models.resource import to_naive_utc, to_naive_user_tz
from odoo.addons.resource.tests.common import TestResourceCommon


class TestIntervals(TestResourceCommon):

    def setUp(self):
        super(TestIntervals, self).setUp()
        # Some data intervals
        #  - first one is included in second one
        #  - second one is extended by third one
        #  - sixth one is included in fourth one
        #  - fifth one is prior to other one
        # Once cleaned: 1 interval 03/02 8-10), 2 intervals 04/02 (8-14 + 17-21)
        self.intervals = [
            self.calendar._interval_new(
                Datetime.from_string('2013-02-04 09:00:00'),
                Datetime.from_string('2013-02-04 11:00:00')
            ), self.calendar._interval_new(
                Datetime.from_string('2013-02-04 08:00:00'),
                Datetime.from_string('2013-02-04 12:00:00')
            ), self.calendar._interval_new(
                Datetime.from_string('2013-02-04 11:00:00'),
                Datetime.from_string('2013-02-04 14:00:00')
            ), self.calendar._interval_new(
                Datetime.from_string('2013-02-04 17:00:00'),
                Datetime.from_string('2013-02-04 21:00:00')
            ), self.calendar._interval_new(
                Datetime.from_string('2013-02-03 08:00:00'),
                Datetime.from_string('2013-02-03 10:00:00')
            ), self.calendar._interval_new(
                Datetime.from_string('2013-02-04 18:00:00'),
                Datetime.from_string('2013-02-04 19:00:00')
            )
        ]

    def test_interval_merge(self):
        cleaned_intervals = self.env['resource.calendar']._interval_merge(self.intervals)
        self.assertEqual(len(cleaned_intervals), 3)
        # First interval: 03, unchanged
        self.assertEqual(cleaned_intervals[0][:2], (Datetime.from_string('2013-02-03 08:00:00'), Datetime.from_string('2013-02-03 10:00:00')))
        # Second interval: 04, 08-14, combining 08-12 and 11-14, 09-11 being inside 08-12
        self.assertEqual(cleaned_intervals[1][:2], (Datetime.from_string('2013-02-04 08:00:00'), Datetime.from_string('2013-02-04 14:00:00')))
        # Third interval: 04, 17-21, 18-19 being inside 17-21
        self.assertEqual(cleaned_intervals[2][:2], (Datetime.from_string('2013-02-04 17:00:00'), Datetime.from_string('2013-02-04 21:00:00')))

    def test_interval_and(self):
        self.assertEqual(self.env['resource.calendar']._interval_and(self.intervals[0], self.intervals[1]),
                         self.calendar._interval_new(Datetime.from_string('2013-02-04 09:00:00'), Datetime.from_string('2013-02-04 11:00:00')))
        self.assertEqual(self.env['resource.calendar']._interval_and(self.intervals[2], self.intervals[3]),
                         None)

    def test_interval_remove(self):
        working_interval = self.calendar._interval_new(Datetime.from_string('2013-02-04 08:00:00'), Datetime.from_string('2013-02-04 18:00:00'))
        result = self.env['resource.calendar']._interval_remove_leaves(working_interval, self.intervals)
        self.assertEqual(len(result), 1)
        # First interval: 04, 14-17
        self.assertEqual(result[0][:2], (Datetime.from_string('2013-02-04 14:00:00'), Datetime.from_string('2013-02-04 17:00:00')))

    def test_interval_schedule_hours(self):
        cleaned_intervals = self.env['resource.calendar']._interval_merge(self.intervals)
        result = self.env['resource.calendar']._interval_schedule_hours(cleaned_intervals, 5.5)
        self.assertEqual(len(result), 2)
        # First interval: 03, 8-10 untouched
        self.assertEqual(result[0][:2], (Datetime.from_string('2013-02-03 08:00:00'), Datetime.from_string('2013-02-03 10:00:00')))
        # First interval: 04, 08-11:30
        self.assertEqual(result[1][:2], (Datetime.from_string('2013-02-04 08:00:00'), Datetime.from_string('2013-02-04 11:30:00')))

    def test_interval_schedule_hours_backwards(self):
        cleaned_intervals = self.env['resource.calendar']._interval_merge(self.intervals)
        result = self.env['resource.calendar']._interval_schedule_hours(cleaned_intervals, 5.5, backwards=True)
        self.assertEqual(len(result), 2)
        # First interval: 03, 8-10 untouched
        self.assertEqual(result[1][:2], (Datetime.from_string('2013-02-04 17:00:00'), Datetime.from_string('2013-02-04 21:00:00')))
        # First interval: 04, 08-11:30
        self.assertEqual(result[0][:2], (Datetime.from_string('2013-02-04 12:30:00'), Datetime.from_string('2013-02-04 14:00:00')))


class TestCalendarBasics(TestResourceCommon):

    def test_calendar_weekdays(self):
        weekdays = self.calendar._get_weekdays()
        self.assertEqual(weekdays, [1, 4])

    def test_calendar_next_day(self):
        # Test: next day: next day after day1 is day4
        date = self.calendar._get_next_work_day(day_date=Date.from_string('2013-02-12'))
        self.assertEqual(date, self.date2.date())

        # Test: next day: next day after day4 is (day1+7)
        date = self.calendar._get_next_work_day(day_date=Date.from_string('2013-02-15'))
        self.assertEqual(date, self.date1.date() + relativedelta(days=7))

        # Test: next day: next day after day4+1 is (day1+7)
        date = self.calendar._get_next_work_day(day_date=Date.from_string('2013-02-15') + relativedelta(days=1))
        self.assertEqual(date, self.date1.date() + relativedelta(days=7))

        # Test: next day: next day after day1-1 is day1
        date = self.calendar._get_next_work_day(day_date=Date.from_string('2013-02-12') + relativedelta(days=-1))
        self.assertEqual(date, self.date1.date())

    def test_calendar_previous_day(self):
        # Test: previous day: previous day before day1 is (day4-7)
        date = self.calendar._get_previous_work_day(day_date=Date.from_string('2013-02-12'))
        self.assertEqual(date, self.date2.date() + relativedelta(days=-7))

        # Test: previous day: previous day before day4 is day1
        date = self.calendar._get_previous_work_day(day_date=Date.from_string('2013-02-15'))
        self.assertEqual(date, self.date1.date())

        # Test: previous day: previous day before day4+1 is day4
        date = self.calendar._get_previous_work_day(day_date=Date.from_string('2013-02-15') + relativedelta(days=1))
        self.assertEqual(date, self.date2.date())

        # Test: previous day: previous day before day1-1 is (day4-7)
        date = self.calendar._get_previous_work_day(day_date=Date.from_string('2013-02-12') + relativedelta(days=-1))
        self.assertEqual(date, self.date2.date() + relativedelta(days=-7))

    def test_calendar_working_day_intervals_no_leaves(self):
        # Test: day0 without leaves: 1 interval
        intervals = self.calendar._get_day_work_intervals(Date.from_string('2013-02-12'), start_time=time(9, 8, 7))
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-12 09:08:07'), Datetime.from_string('2013-02-12 16:00:00')))
        self.assertEqual(intervals[0][2]['attendances'], self.att_1)

        # Test: day1, beginning at 10:30 -> work from 10:30 (arrival) until 16:00
        intervals = self.calendar._get_day_work_intervals(Date.from_string('2013-02-19'), start_time=time(10, 30, 0))
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-19 10:30:00'), Datetime.from_string('2013-02-19 16:00:00')))
        self.assertEqual(intervals[0][2]['attendances'], self.att_1)

        # Test: day3 without leaves: 2 interval
        intervals = self.calendar._get_day_work_intervals(Date.from_string('2013-02-15'), start_time=time(10, 11, 12))
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00')))
        self.assertEqual(intervals[1][:2], (Datetime.from_string('2013-02-15 16:00:00'), Datetime.from_string('2013-02-15 23:00:00')))
        self.assertEqual(intervals[0][2]['attendances'], self.att_2)
        self.assertEqual(intervals[1][2]['attendances'], self.att_3)

    def test_calendar_working_day_intervals_leaves_generic(self):
        # Test: day0 with leaves outside range: 1 interval
        intervals = self.calendar._get_day_work_intervals(Date.from_string('2013-02-12'), start_time=time(7, 0, 0), compute_leaves=True)
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-12 08:00:00'), Datetime.from_string('2013-02-12 16:00:00')))

        # Test: day0 with leaves: 2 intervals because of leave between 9 and 12, ending at 15:45:30
        intervals = self.calendar._get_day_work_intervals(Date.from_string('2013-02-19'),
                                                          start_time=time(8, 15, 0),
                                                          end_time=time(15, 45, 30),
                                                          compute_leaves=True)
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-19 08:15:00'), Datetime.from_string('2013-02-19 09:00:00')))
        self.assertEqual(intervals[1][:2], (Datetime.from_string('2013-02-19 12:00:00'), Datetime.from_string('2013-02-19 15:45:30')))
        self.assertEqual(intervals[0][2]['attendances'], self.att_1)
        self.assertEqual(intervals[0][2]['leaves'], self.leave1)
        self.assertEqual(intervals[1][2]['attendances'], self.att_1)
        self.assertEqual(intervals[0][2]['leaves'], self.leave1)

    def test_calendar_working_day_intervals_leaves_resource(self):
        # Test: day1+14 on leave, with resource leave computation
        intervals = self.calendar._get_day_work_intervals(
            Date.from_string('2013-02-26'),
            start_time=time(7, 0, 0),
            compute_leaves=True,
            resource_id=self.resource1_id
        )
        # Result: nothing, because on leave
        self.assertEqual(len(intervals), 0)

    def test_calendar_working_day_intervals_limited_attendances(self):
        """ Test attendances limited in time. """
        attendance = self.env['resource.calendar.attendance'].search(
            [('name', '=', 'Att3')])
        attendance.write({
            'date_from': self.date2 + relativedelta(days=7),
            'date_to': False,
        })
        intervals = self.calendar._get_day_work_intervals(self.date2.date(), start_time=self.date2.time())
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00')))

        attendance.write({
            'date_from': False,
            'date_to': self.date2 - relativedelta(days=7),
        })
        intervals = self.calendar._get_day_work_intervals(self.date2.date(), start_time=self.date2.time())
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00')))

        attendance.write({
            'date_from': self.date2 + relativedelta(days=7),
            'date_to': self.date2 - relativedelta(days=7),
        })
        intervals = self.calendar._get_day_work_intervals(self.date2.date(), start_time=self.date2.time())
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00')))

        attendance.write({
            'date_from': self.date2,
            'date_to': self.date2,
        })
        intervals = self.calendar._get_day_work_intervals(self.date2.date(), start_time=self.date2.time())
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0][:2], (Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00')))
        self.assertEqual(intervals[1][:2], (Datetime.from_string('2013-02-15 16:00:00'), Datetime.from_string('2013-02-15 23:00:00')))

    def test_calendar_working_hours_of_date(self):
        # Test: day1, beginning at 10:30 -> work from 10:30 (arrival) until 16:00
        wh = self.calendar.get_work_hours_count(Datetime.from_string('2013-02-19 10:30:00'), Datetime.from_string('2013-02-19 18:00:00'), self.resource1_id, compute_leaves=False)
        self.assertEqual(wh, 5.5)


class ResourceWorkingHours(TestResourceCommon):

    def test_calendar_working_hours(self):
        # new API: resource without leaves
        # res: 2 weeks -> 40 hours
        res = self.calendar.get_work_hours_count(
            Datetime.from_string('2013-02-12 06:00:00'),
            Datetime.from_string('2013-02-22 23:00:00'),
            self.resource1_id,
            compute_leaves=False)
        self.assertEqual(res, 40.0)

    def test_calendar_working_hours_leaves(self):
        # new API: resource and leaves
        # res: 2 weeks -> 40 hours - (3+4) leave hours
        res = self.calendar.get_work_hours_count(
            Datetime.from_string('2013-02-12 06:00:00'),
            Datetime.from_string('2013-02-22 23:00:00'),
            self.resource1_id,
            compute_leaves=True)
        self.assertEqual(res, 33.0)

    def test_calendar_working_hours_24(self):
        self.att_4 = self.env['resource.calendar.attendance'].create({
            'name': 'Att4',
            'calendar_id': self.calendar.id,
            'dayofweek': '2',
            'hour_from': 0,
            'hour_to': 24
        })
        res = self.calendar.get_work_hours_count(
            Datetime.from_string('2018-06-19 23:00:00'),
            Datetime.from_string('2018-06-21 01:00:00'),
            self.resource1_id,
            compute_leaves=True)
        self.assertAlmostEqual(res, 24.0)

    def test_calendar_timezone(self):
        # user in timezone UTC-9 asks for work hours
        #  Limits: between 2013-02-19 10:00:00 and 2013-02-26 15:30:00 (User TZ)
        #          between 2013-02-19 19:00:00 and 2013-02-27 00:30:00 (UTC)
        # Leaves:  between 2013-02-21 10:00:00 and 2013-02-26 12:00:00 (User TZ)
        # res: 19/02 (10-16 (beginning)) + 22/02 (0 (leave)) + 26/02 (12-15.30 (leave+ending))
        self.env.user.tz = 'US/Alaska'
        (self.leave1 | self.leave2 | self.leave3).unlink()
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'Timezoned Leaves',
            'calendar_id': self.calendar.id,
            'resource_id': self.resource1_id,
            'date_from': to_naive_utc(Datetime.from_string('2013-02-21 10:00:00'), self.env.user),
            'date_to': to_naive_utc(Datetime.from_string('2013-02-26 12:00:00'), self.env.user)
        })
        res = self.calendar.get_work_hours_count(
            to_naive_utc(Datetime.from_string('2013-02-19 10:00:00'), self.env.user),
            to_naive_utc(Datetime.from_string('2013-02-26 15:30:00'), self.env.user),
            self.resource1_id,
            compute_leaves=True)
        self.assertEqual(res, 9.5)

    def test_calendar_hours_scheduling_backward(self):
        res = self.calendar._schedule_hours(-40, day_dt=Datetime.from_string('2013-02-12 09:00:00'))
        # current day, limited at 09:00 because of day_dt specified -> 1 hour
        self.assertEqual(res[-1][:2], (Datetime.from_string('2013-02-12 08:00:00'), Datetime.from_string('2013-02-12 09:00:00')))
        # previous days: 5+7 hours / 8 hours / 5+7 hours -> 32 hours
        self.assertEqual(res[-2][:2], (Datetime.from_string('2013-02-08 16:00:00'), Datetime.from_string('2013-02-08 23:00:00')))
        self.assertEqual(res[-3][:2], (Datetime.from_string('2013-02-08 08:00:00'), Datetime.from_string('2013-02-08 13:00:00')))
        self.assertEqual(res[-4][:2], (Datetime.from_string('2013-02-05 08:00:00'), Datetime.from_string('2013-02-05 16:00:00')))
        self.assertEqual(res[-5][:2], (Datetime.from_string('2013-02-01 16:00:00'), Datetime.from_string('2013-02-01 23:00:00')))
        self.assertEqual(res[-6][:2], (Datetime.from_string('2013-02-01 08:00:00'), Datetime.from_string('2013-02-01 13:00:00')))
        # 7 hours remaining
        self.assertEqual(res[-7][:2], (Datetime.from_string('2013-01-29 09:00:00'), Datetime.from_string('2013-01-29 16:00:00')))

        # Compute scheduled hours
        td = timedelta()
        for item in res:
            td += item[1] - item[0]
        self.assertEqual(td.total_seconds() / 3600.0, 40.0)

        res = self.calendar.plan_hours(-40, day_dt=Datetime.from_string('2013-02-12 09:00:00'))
        self.assertEqual(res, Datetime.from_string('2013-01-29 09:00:00'))

    def test_calendar_hours_scheduling_forward(self):
        res = self.calendar._schedule_hours(40, day_dt=Datetime.from_string('2013-02-12 09:00:00'))
        self.assertEqual(res[0][:2], (Datetime.from_string('2013-02-12 09:00:00'), Datetime.from_string('2013-02-12 16:00:00')))
        self.assertEqual(res[1][:2], (Datetime.from_string('2013-02-15 08:00:00'), Datetime.from_string('2013-02-15 13:00:00')))
        self.assertEqual(res[2][:2], (Datetime.from_string('2013-02-15 16:00:00'), Datetime.from_string('2013-02-15 23:00:00')))
        self.assertEqual(res[3][:2], (Datetime.from_string('2013-02-19 08:00:00'), Datetime.from_string('2013-02-19 16:00:00')))
        self.assertEqual(res[4][:2], (Datetime.from_string('2013-02-22 08:00:00'), Datetime.from_string('2013-02-22 13:00:00')))
        self.assertEqual(res[5][:2], (Datetime.from_string('2013-02-22 16:00:00'), Datetime.from_string('2013-02-22 23:00:00')))
        self.assertEqual(res[6][:2], (Datetime.from_string('2013-02-26 08:00:00'), Datetime.from_string('2013-02-26 09:00:00')))

        td = timedelta()
        for item in res:
            td += item[1] - item[0]
        self.assertEqual(td.total_seconds() / 3600.0, 40.0)

        res = self.calendar.plan_hours(40, day_dt=Datetime.from_string('2013-02-12 09:00:00'))
        self.assertEqual(res, Datetime.from_string('2013-02-26 09:00:00'))

    def test_calendar_hours_scheduling_timezone(self):
        # user in timezone UTC-9 asks for work hours
        self.env.user.tz = 'US/Alaska'
        res = self.calendar.plan_hours(
            42,
            to_naive_utc(Datetime.from_string('2013-02-12 09:25:00'), self.env.user))
        self.assertEqual(res, to_naive_utc(Datetime.from_string('2013-02-26 11:25:00'), self.env.user))

    def test_calendar_hours_scheduling_timezone_2(self):
        # Call schedule_hours for a user in Autralia, Sydney (GMT+10)
        # Two cases:
        # - start at 2013-02-15 08:00:00 => 2013-02-14 21:00:00 in UTC
        # - start at 2013-02-15 11:00:00 => 2013-02-15 00:00:00 in UTC
        self.env.user.tz = 'Australia/Sydney'
        self.env['resource.calendar.attendance'].create({
            'name': 'Day3 - 1',
            'dayofweek': '3',
            'hour_from': 8,
            'hour_to': 12,
            'calendar_id': self.calendar.id,
        })
        self.env['resource.calendar.attendance'].create({
            'name': 'Day3 - 2',
            'dayofweek': '3',
            'hour_from': 13,
            'hour_to': 17,
            'calendar_id': self.calendar.id,
        })
        hours = 1.0/60.0
        for test_date in ['2013-02-15 08:00:00', '2013-02-15 11:00:00']:
            start_dt = Datetime.from_string(test_date)
            start_dt_utc = to_naive_utc(start_dt, self.env.user)
            res = self.calendar._schedule_hours(hours, start_dt_utc)
            self.assertEqual(
                [(start_dt_utc, start_dt_utc.replace(minute=1))], res,
                'resource_calendar: wrong schedule_hours computation')

    def test_calendar_hours_scheduling_forward_leaves_resource(self):
        res = self.calendar._schedule_hours(
            40, day_dt=Datetime.from_string('2013-02-12 09:00:00'),
            compute_leaves=True, resource_id=self.resource1_id
        )
        self.assertEqual(res[0][:2], (Datetime.from_string('2013-02-12 09:00:00'), Datetime.from_string('2013-02-12 16:00:00')))
        self.assertEqual(res[1][:2], (Datetime.from_string('2013-02-15 08:00:00'), Datetime.from_string('2013-02-15 13:00:00')))
        self.assertEqual(res[2][:2], (Datetime.from_string('2013-02-15 16:00:00'), Datetime.from_string('2013-02-15 23:00:00')))
        self.assertEqual(res[3][:2], (Datetime.from_string('2013-02-19 08:00:00'), Datetime.from_string('2013-02-19 09:00:00')))
        self.assertEqual(res[4][:2], (Datetime.from_string('2013-02-19 12:00:00'), Datetime.from_string('2013-02-19 16:00:00')))
        self.assertEqual(res[5][:2], (Datetime.from_string('2013-02-22 08:00:00'), Datetime.from_string('2013-02-22 09:00:00')))
        self.assertEqual(res[6][:2], (Datetime.from_string('2013-02-22 16:00:00'), Datetime.from_string('2013-02-22 23:00:00')))
        self.assertEqual(res[7][:2], (Datetime.from_string('2013-03-01 11:30:00'), Datetime.from_string('2013-03-01 13:00:00')))
        self.assertEqual(res[8][:2], (Datetime.from_string('2013-03-01 16:00:00'), Datetime.from_string('2013-03-01 22:30:00')))

        td = timedelta()
        for item in res:
            td += item[1] - item[0]
        self.assertEqual(td.total_seconds() / 3600.0, 40.0)

    def test_calendar_days_scheduling(self):
        res = self.calendar.plan_days(5, Datetime.from_string('2013-02-12 09:08:07') )
        self.assertEqual(res.date(), Datetime.from_string('2013-02-26 00:00:00').date(), 'resource_calendar: wrong days scheduling')
        res = self.calendar.plan_days(-2, Datetime.from_string('2013-02-12 09:08:07') )
        self.assertEqual(res.date(), Datetime.from_string('2013-02-08 00:00:00').date(), 'resource_calendar: wrong days scheduling')

        res = self.calendar.plan_days(
            5, Datetime.from_string('2013-02-12 09:08:07'),
            compute_leaves=True, resource_id=self.resource1_id)
        self.assertEqual(res.date(), Datetime.from_string('2013-03-01 00:00:00').date(), 'resource_calendar: wrong days scheduling')

    def test_calendar_days_scheduling_timezone(self):
        self.env.user.tz = 'US/Alaska'
        res = self.calendar.plan_days(5, to_naive_utc(Datetime.from_string('2013-02-12 09:08:07'), self.env.user))
        self.assertEqual(to_naive_user_tz(res, self.env.user).date(), Datetime.from_string('2013-02-26 00:00:00').date())


WAR_START = date(1932, 11, 2)
WAR_END = date(1932, 12, 10)


class TestWorkDays(TestResourceCommon):

    def _make_attendance(self, weekday, **kw):
        data = {
            'name': babel.dates.get_day_names()[weekday],
            'dayofweek': str(weekday),
            'hour_from': 9,
            'hour_to': 17,
        }
        data.update(kw)
        return data

    def setUp(self):
        super(TestWorkDays, self).setUp()
        # trivial 5/7 9-17 resource calendar
        self.calendar.write({
            'attendance_ids': [
                (0, 0, self._make_attendance(i))
                for i in range(5)
            ]
        })

        self._days = [dt.date() for dt in rrule.rrule(rrule.DAILY, dtstart=WAR_START, until=WAR_END)]

    def test_trivial_calendar_no_leaves(self):
        """ If leaves are not involved, only calendar attendances (basic
        company configuration) are taken in account
        """
        r = self.env['resource.resource'].create({
            'name': "Trivial Calendar",
            'calendar_id': self.calendar.id
        })

        # with the trivial calendar, all days are work days except for
        # saturday and sunday
        self.assertEqual(
            [d for d in self._days if d.weekday() not in (5, 6)],
            list(r.calendar_id._iter_work_days(WAR_START, WAR_END, r.id))
        )

    def test_global_leaves(self):
        self.env['resource.calendar.leaves'].create({
            'calendar_id': self.calendar.id,
            'date_from': '1932-11-09 00:00:00',
            'date_to': '1932-11-12 23:59:59',
        })

        r1 = self.env['resource.resource'].create({
            'name': "Resource 1",
            'calendar_id': self.calendar.id
        })
        r2 = self.env['resource.resource'].create({
            'name': "Resource 2",
            'calendar_id': self.calendar.id
        })

        days = [
            d for d in self._days
            if d.weekday() not in (5, 6)
            if d < date(1932, 11, 9) or d > date(1932, 11, 12)
        ]
        self.assertEqual(days, list(r1.calendar_id._iter_work_days(WAR_START, WAR_END, r1.id)))
        self.assertEqual(days, list(r2.calendar_id._iter_work_days(WAR_START, WAR_END, r2.id)))

    def test_personal_leaves(self):
        """ Leaves with a resource_id apply only to that resource
        """
        r1 = self.env['resource.resource'].create({
            'name': "Resource 1",
            'calendar_id': self.calendar.id
        })
        r2 = self.env['resource.resource'].create({
            'name': "Resource 2",
            'calendar_id': self.calendar.id
        })
        self.env['resource.calendar.leaves'].create({
            'calendar_id': self.calendar.id,
            'date_from': '1932-11-09 00:00:00',
            'date_to': '1932-11-12 23:59:59',
            'resource_id': r2.id
        })

        weekdays = [d for d in self._days if d.weekday() not in (5, 6)]
        self.assertEqual(weekdays, list(r1.calendar_id._iter_work_days(WAR_START, WAR_END, r1.id)))
        self.assertEqual([
            d for d in weekdays if d < date(1932, 11, 9) or d > date(1932, 11, 12)],
            list(r2.calendar_id._iter_work_days(WAR_START, WAR_END, r2.id))
        )

    def test_mixed_leaves(self):
        r = self.env['resource.resource'].create({
            'name': "Resource 1",
            'calendar_id': self.calendar.id
        })
        self.env['resource.calendar.leaves'].create({
            'calendar_id': self.calendar.id,
            'date_from': '1932-11-09 00:00:00',
            'date_to': '1932-11-12 23:59:59',
        })
        self.env['resource.calendar.leaves'].create({
            'calendar_id': self.calendar.id,
            'date_from': '1932-12-02 00:00:00',
            'date_to': '1932-12-31 23:59:59',
            'resource_id': r.id
        })

        self.assertEqual([
            d for d in self._days
            if d.weekday() not in (5, 6)
            if d < date(1932, 11, 9) or d > date(1932, 11, 12)
            if d < date(1932, 12, 2)],
            list(r.calendar_id._iter_work_days(WAR_START, WAR_END, r.id))
        )

        # _is_work_day is built on _iter_work_days, but it's probably a good
        # idea to ensure it does do what it should
        self.assertTrue(r.calendar_id._is_work_day(date(1932, 11, 8), r.id))
        self.assertTrue(r.calendar_id._is_work_day(date(1932, 11, 14), r.id))
        self.assertTrue(r.calendar_id._is_work_day(date(1932, 12, 1), r.id))

        self.assertFalse(r.calendar_id._is_work_day(date(1932, 11, 11), r.id))  # global leave
        self.assertFalse(r.calendar_id._is_work_day(date(1932, 11, 13), r.id))  # sun
        self.assertFalse(r.calendar_id._is_work_day(date(1932, 11, 19), r.id))  # sat
        self.assertFalse(r.calendar_id._is_work_day(date(1932, 11, 20), r.id))  # sun
        self.assertFalse(r.calendar_id._is_work_day(date(1932, 12, 6), r.id))  # personal leave


class TestResourceMixin(TestResourceCommon):

    def setUp(self):
        super(TestResourceMixin, self).setUp()
        self.lost_user = self.env['res.users'].with_context(
            no_reset_password=True,
            mail_create_nosubscribe=True
        ).create({
            'name': 'Désiré Boideladodo',
            'login': 'desire',
            'tz': 'Indian/Reunion',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        self.test = self.env['resource.test'].with_context(default_resource_calendar_id=self.calendar.id).create({'name': 'Test'})

    def test_basics(self):
        self.assertEqual(self.env['resource.test'].create({'name': 'Test'}).resource_calendar_id, self.env.user.company_id.resource_calendar_id)
        self.assertEqual(self.test.resource_calendar_id, self.calendar)

    def test_work_days_count(self):
        # user in timezone UTC-9 asks for work hours
        self.env.user.tz = 'US/Alaska'

        res = self.test.get_work_days_count(
            to_naive_utc(Datetime.from_string('2013-02-12 06:00:00'), self.env.user),
            to_naive_utc(Datetime.from_string('2013-02-22 23:00:00'), self.env.user))
        self.assertEqual(res, 3.75)  # generic leaves, 3 hours

        res = self.test.get_work_days_count(
            to_naive_utc(Datetime.from_string('2013-02-12 06:00:00'), self.env.user),
            to_naive_utc(Datetime.from_string('2013-02-22 20:00:00'), self.env.user))
        self.assertEqual(res, 3.5)  # last day is truncated of 3 hours on 12)

        self.env['resource.calendar.leaves'].create({
            'name': 'Timezoned Leaves',
            'calendar_id': self.test.resource_calendar_id.id,
            'resource_id': self.test.resource_id.id,
            'date_from': to_naive_utc(Datetime.from_string('2013-02-13 10:00:00'), self.env.user),
            'date_to': to_naive_utc(Datetime.from_string('2013-02-17 12:00:00'), self.env.user)
        })

        res = self.test.get_work_days_count(
            to_naive_utc(Datetime.from_string('2013-02-12 06:00:00'), self.env.user),
            to_naive_utc(Datetime.from_string('2013-02-22 20:00:00'), self.env.user))
        self.assertEqual(res, 2.5)  # one day is on leave and last day is truncated of 3 hours on 12)

    def test_work_days_count_timezones_ultra(self):
        # user in timezone UTC+4 is attached to the resource and create leaves
        self.test.resource_id.write({
            'user_id': self.lost_user.id,
        })
        reunion_leave = self.env['resource.calendar.leaves'].sudo(self.lost_user).create({
            'name': 'Timezoned Leaves',
            'calendar_id': self.test.resource_calendar_id.id,
            'resource_id': self.test.resource_id.id,
            'date_from': to_naive_utc(Datetime.from_string('2013-02-12 10:00:00'), self.lost_user),
            'date_to': to_naive_utc(Datetime.from_string('2013-02-12 12:00:00'), self.lost_user)
        })
        self.assertEqual(reunion_leave.tz, 'Indian/Reunion')

        # user in timezone UTC-9 read and manipulate leaves
        self.env.user.tz = 'US/Alaska'
        res = self.test.get_work_days_data(
            to_naive_utc(Datetime.from_string('2013-02-12 06:00:00'), self.env.user),
            to_naive_utc(Datetime.from_string('2013-02-12 20:00:00'), self.env.user))
        self.assertEqual(res['days'], 0.75)
        self.assertEqual(res['hours'], 6.0)

        # user in timezone UTC+4 read and manipulate leaves
        res = self.test.sudo(self.lost_user).get_work_days_data(
            to_naive_utc(Datetime.from_string('2013-02-12 06:00:00'), self.env.user),
            to_naive_utc(Datetime.from_string('2013-02-12 20:00:00'), self.env.user))
        self.assertEqual(res['days'], 0.75)
        self.assertEqual(res['hours'], 6.0)
