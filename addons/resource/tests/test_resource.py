# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.dates

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from odoo.fields import Date, Datetime
from odoo.tools import float_compare
from odoo.addons.resource.tests.common import TestResourceCommon
from odoo.tests import TransactionCase


class TestIntervals(TestResourceCommon):

    def setUp(self):
        super(TestResourceCommon, self).setUp()
        # Some data intervals
        #  - first one is included in second one
        #  - second one is extended by third one
        #  - sixth one is included in fourth one
        #  - fifth one is prior to other one
        # Once cleaned: 1 interval 03/02 8-10), 2 intervals 04/02 (8-14 + 17-21)
        self.intervals = [
            (
                Datetime.from_string('2013-02-04 09:00:00'),
                Datetime.from_string('2013-02-04 11:00:00')
            ), (
                Datetime.from_string('2013-02-04 08:00:00'),
                Datetime.from_string('2013-02-04 12:00:00')
            ), (
                Datetime.from_string('2013-02-04 11:00:00'),
                Datetime.from_string('2013-02-04 14:00:00')
            ), (
                Datetime.from_string('2013-02-04 17:00:00'),
                Datetime.from_string('2013-02-04 21:00:00')
            ), (
                Datetime.from_string('2013-02-03 08:00:00'),
                Datetime.from_string('2013-02-03 10:00:00')
            ), (
                Datetime.from_string('2013-02-04 18:00:00'),
                Datetime.from_string('2013-02-04 19:00:00')
            )
        ]

    def test_interval_clean(self):
        cleaned_intervals = self.env['resource.calendar'].interval_clean(self.intervals)
        self.assertEqual(len(cleaned_intervals), 3)
        # First interval: 03, unchanged
        self.assertEqual(cleaned_intervals[0], (Datetime.from_string('2013-02-03 08:00:00'), Datetime.from_string('2013-02-03 10:00:00')))
        # Second interval: 04, 08-14, combining 08-12 and 11-14, 09-11 being inside 08-12
        self.assertEqual(cleaned_intervals[1], (Datetime.from_string('2013-02-04 08:00:00'), Datetime.from_string('2013-02-04 14:00:00')))
        # Third interval: 04, 17-21, 18-19 being inside 17-21
        self.assertEqual(cleaned_intervals[2], (Datetime.from_string('2013-02-04 17:00:00'), Datetime.from_string('2013-02-04 21:00:00')))

    def test_interval_remove(self):
        working_interval = (Datetime.from_string('2013-02-04 08:00:00'), Datetime.from_string('2013-02-04 18:00:00'))
        result = self.env['resource.calendar'].interval_remove_leaves(working_interval, self.intervals)
        self.assertEqual(len(result), 1)
        # First interval: 04, 14-17
        self.assertEqual(result[0], (Datetime.from_string('2013-02-04 14:00:00'), Datetime.from_string('2013-02-04 17:00:00')))

    def test_interval_schedule_hours(self):
        cleaned_intervals = self.env['resource.calendar'].interval_clean(self.intervals)
        result = self.env['resource.calendar'].interval_schedule_hours(cleaned_intervals, 5.5)
        self.assertEqual(len(result), 2)
        # First interval: 03, 8-10 untouched
        self.assertEqual(result[0], (Datetime.from_string('2013-02-03 08:00:00'), Datetime.from_string('2013-02-03 10:00:00')))
        # First interval: 04, 08-11:30
        self.assertEqual(result[1], (Datetime.from_string('2013-02-04 08:00:00'), Datetime.from_string('2013-02-04 11:30:00')))

    def test_interval_schedule_hours_backwards(self):
        cleaned_intervals = self.env['resource.calendar'].interval_clean(self.intervals)
        cleaned_intervals.reverse()
        result = self.env['resource.calendar'].interval_schedule_hours(cleaned_intervals, 5.5, remove_at_end=False)
        self.assertEqual(len(result), 2)
        # First interval: 03, 8-10 untouched
        self.assertEqual(result[0], (Datetime.from_string('2013-02-04 17:00:00'), Datetime.from_string('2013-02-04 21:00:00')))
        # First interval: 04, 08-11:30
        self.assertEqual(result[1], (Datetime.from_string('2013-02-04 12:30:00'), Datetime.from_string('2013-02-04 14:00:00')))


class TestCalendarBasics(TestResourceCommon):

    def test_calendar_weekdays(self):
        weekdays = self.calendar.get_weekdays()
        self.assertEqual(weekdays, [1, 4])

    def test_calendar_next_day(self):
        # Test: next day: next day after day1 is day4
        date = self.calendar.get_next_day(day_date=Date.from_string('2013-02-12'))
        self.assertEqual(date, self.date2.date())

        # Test: next day: next day after day4 is (day1+7)
        date = self.calendar.get_next_day(day_date=Date.from_string('2013-02-15'))
        self.assertEqual(date, self.date1.date() + relativedelta(days=7))

        # Test: next day: next day after day4+1 is (day1+7)
        date = self.calendar.get_next_day(day_date=Date.from_string('2013-02-15') + relativedelta(days=1))
        self.assertEqual(date, self.date1.date() + relativedelta(days=7))

        # Test: next day: next day after day1-1 is day1
        date = self.calendar.get_next_day(day_date=Date.from_string('2013-02-12') + relativedelta(days=-1))
        self.assertEqual(date, self.date1.date())

    def test_calendar_previous_day(self):
        # Test: previous day: previous day before day1 is (day4-7)
        date = self.calendar.get_previous_day(day_date=Date.from_string('2013-02-12'))
        self.assertEqual(date, self.date2.date() + relativedelta(days=-7))

        # Test: previous day: previous day before day4 is day1
        date = self.calendar.get_previous_day(day_date=Date.from_string('2013-02-15'))
        self.assertEqual(date, self.date1.date())

        # Test: previous day: previous day before day4+1 is day4
        date = self.calendar.get_previous_day(day_date=Date.from_string('2013-02-15') + relativedelta(days=1))
        self.assertEqual(date, self.date2.date())

        # Test: previous day: previous day before day1-1 is (day4-7)
        date = self.calendar.get_previous_day(day_date=Date.from_string('2013-02-12') + relativedelta(days=-1))
        self.assertEqual(date, self.date2.date() + relativedelta(days=-7))

    def test_calendar_working_day_intervals_no_leaves(self):
        # Test: day0 without leaves: 1 interval
        intervals = self.calendar.get_working_intervals_of_day(start_dt=Datetime.from_string('2013-02-12 09:08:07'))
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0], (Datetime.from_string('2013-02-12 09:08:07'), Datetime.from_string('2013-02-12 16:00:00')))

        # Test: day1, beginning at 10:30 -> work from 10:30 (arrival) until 16:00
        intervals = self.calendar.get_working_intervals_of_day(start_dt=Datetime.from_string('2013-02-19 10:30:00'))
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0], (Datetime.from_string('2013-02-19 10:30:00'), Datetime.from_string('2013-02-19 16:00:00')))

        # Test: day3 without leaves: 2 interval
        intervals = self.calendar.get_working_intervals_of_day(start_dt=Datetime.from_string('2013-02-15 10:11:12'))
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0], (Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00')))
        self.assertEqual(intervals[1], (Datetime.from_string('2013-02-15 16:00:00'), Datetime.from_string('2013-02-15 23:00:00')))

    def test_calendar_working_day_intervals_leaves_generic(self):
        # Test: day0 with leaves outside range: 1 interval
        intervals = self.calendar.get_working_intervals_of_day(start_dt=Datetime.from_string('2013-02-12 07:00:00'), compute_leaves=True)
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0], (Datetime.from_string('2013-02-12 08:00:00'), Datetime.from_string('2013-02-12 16:00:00')))

        # Test: day0 with leaves: 2 intervals because of leave between 9 ans 12, ending at 15:45:30
        intervals = self.calendar.get_working_intervals_of_day(start_dt=Datetime.from_string('2013-02-19 08:15:00'),
                                                               end_dt=Datetime.from_string('2013-02-19 15:45:30'),
                                                               compute_leaves=True)
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0], (Datetime.from_string('2013-02-19 08:15:00'), Datetime.from_string('2013-02-19 09:00:00')))
        self.assertEqual(intervals[1], (Datetime.from_string('2013-02-19 12:00:00'), Datetime.from_string('2013-02-19 15:45:30')))

    def test_calendar_working_day_intervals_leaves_resource(self):
        # Test: day1+14 on leave, with resource leave computation
        intervals = self.calendar.get_working_intervals_of_day(
            Datetime.from_string('2013-02-26 07:00:00'),
            compute_leaves=True,
            resource_id=self.resource1_id
        )
        # Result: nothing, because on leave
        self.assertEqual(len(intervals), 0, 'resource_calendar: wrong working interval/day computing')

    def test_calendar_working_day_intervals_limited_attendances(self):
        """ Test attendances limited in time. """
        attendance = self.env['resource.calendar.attendance'].search(
            [('name', '=', 'Att3')])
        attendance.write({
            'date_from': self.date2 + relativedelta(days=7),
            'date_to': False,
        })
        intervals = self.calendar.get_working_intervals_of_day(start_dt=self.date2)
        self.assertEqual(intervals, [(Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00'))])

        attendance.write({
            'date_from': False,
            'date_to': self.date2 - relativedelta(days=7),
        })
        intervals = self.calendar.get_working_intervals_of_day(start_dt=self.date2)
        self.assertEqual(intervals, [(Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00'))])

        attendance.write({
            'date_from': self.date2 + relativedelta(days=7),
            'date_to': self.date2 - relativedelta(days=7),
        })
        intervals = self.calendar.get_working_intervals_of_day(start_dt=self.date2)
        self.assertEqual(intervals, [(Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00'))])

        attendance.write({
            'date_from': self.date2,
            'date_to': self.date2,
        })
        intervals = self.calendar.get_working_intervals_of_day(start_dt=self.date2)
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0], (Datetime.from_string('2013-02-15 10:11:12'), Datetime.from_string('2013-02-15 13:00:00')))
        self.assertEqual(intervals[1], (Datetime.from_string('2013-02-15 16:00:00'), Datetime.from_string('2013-02-15 23:00:00')))

    def test_calendar_working_hours_of_date(self):
        # Test: day1, beginning at 10:30 -> work from 10:30 (arrival) until 16:00
        wh = self.calendar.get_working_hours_of_date(start_dt=Datetime.from_string('2013-02-19 10:30:00'))
        self.assertEqual(wh, 5.5, 'resource_calendar: wrong working interval / day time computing')


class ResourceWorkingHours(TestResourceCommon):

    def test_calendar_working_hours(self):
        # old API: resource without leaves
        # res: 2 weeks -> 40 hours
        res = self.calendar._interval_hours_get(
            Datetime.from_string('2013-02-12 06:00:00'),
            Datetime.from_string('2013-02-22 23:00:00'),
            resource_id=self.resource1_id, exclude_leaves=True)
        self.assertEqual(res, 40.0)

        # new API: resource without leaves
        # res: 2 weeks -> 40 hours
        res = self.calendar.get_working_hours(
            Datetime.from_string('2013-02-12 06:00:00'),
            Datetime.from_string('2013-02-22 23:00:00'),
            compute_leaves=False, resource_id=self.resource1_id)
        self.assertEqual(res, 40.0)

    def test_calendar_working_hours_leaves(self):
        # old API: resource and leaves
        # res: 2 weeks -> 40 hours - (3+4) leave hours
        res = self.calendar._interval_hours_get(
            Datetime.from_string('2013-02-12 06:00:00'),
            Datetime.from_string('2013-02-22 23:00:00'),
            resource_id=self.resource1_id, exclude_leaves=False)
        self.assertEqual(res, 33.0)

        # new API: resource and leaves
        # res: 2 weeks -> 40 hours - (3+4) leave hours
        res = self.calendar.get_working_hours(
            Datetime.from_string('2013-02-12 06:00:00'),
            Datetime.from_string('2013-02-22 23:00:00'),
            compute_leaves=True, resource_id=self.resource1_id)
        self.assertEqual(res, 33.0)

    def test_calendar_working_hours_default_calendar(self):
        # Test without calendar and default_interval
        res = self.env['resource.calendar'].with_context(tz='UTC').get_working_hours(
            Datetime.from_string('2013-02-12 06:00:00'),
            Datetime.from_string('2013-02-15 23:00:00'),
            compute_leaves=True, resource_id=self.resource1_id,
            default_interval=(8, 16))
        self.assertEqual(res, 32.0)

    def test_calendar_hours_scheduling_backward(self):
        res = self.calendar.schedule_hours(-40, day_dt=Datetime.from_string('2013-02-12 09:00:00'))
        # current day, limited at 09:00 because of day_dt specified -> 1 hour
        self.assertEqual(res[-1], (Datetime.from_string('2013-02-12 08:00:00'), Datetime.from_string('2013-02-12 09:00:00')))
        # previous days: 5+7 hours / 8 hours / 5+7 hours -> 32 hours
        self.assertEqual(res[-2], (Datetime.from_string('2013-02-08 16:00:00'), Datetime.from_string('2013-02-08 23:00:00')))
        self.assertEqual(res[-3], (Datetime.from_string('2013-02-08 08:00:00'), Datetime.from_string('2013-02-08 13:00:00')))
        self.assertEqual(res[-4], (Datetime.from_string('2013-02-05 08:00:00'), Datetime.from_string('2013-02-05 16:00:00')))
        self.assertEqual(res[-5], (Datetime.from_string('2013-02-01 16:00:00'), Datetime.from_string('2013-02-01 23:00:00')))
        self.assertEqual(res[-6], (Datetime.from_string('2013-02-01 08:00:00'), Datetime.from_string('2013-02-01 13:00:00')))
        # 7 hours remaining
        self.assertEqual(res[-7], (Datetime.from_string('2013-01-29 09:00:00'), Datetime.from_string('2013-01-29 16:00:00')))

        # Compute scheduled hours
        td = timedelta()
        for item in res:
            td += item[1] - item[0]
        self.assertEqual(seconds(td) / 3600.0, 40.0)

    def test_calendar_hours_scheduling_forward(self):
        res = self.calendar.schedule_hours(40, day_dt=Datetime.from_string('2013-02-12 09:00:00'))
        self.assertEqual(res[0], (Datetime.from_string('2013-02-12 09:00:00'), Datetime.from_string('2013-02-12 16:00:00')))
        self.assertEqual(res[1], (Datetime.from_string('2013-02-15 08:00:00'), Datetime.from_string('2013-02-15 13:00:00')))
        self.assertEqual(res[2], (Datetime.from_string('2013-02-15 16:00:00'), Datetime.from_string('2013-02-15 23:00:00')))
        self.assertEqual(res[3], (Datetime.from_string('2013-02-19 08:00:00'), Datetime.from_string('2013-02-19 16:00:00')))
        self.assertEqual(res[4], (Datetime.from_string('2013-02-22 08:00:00'), Datetime.from_string('2013-02-22 13:00:00')))
        self.assertEqual(res[5], (Datetime.from_string('2013-02-22 16:00:00'), Datetime.from_string('2013-02-22 23:00:00')))
        self.assertEqual(res[6], (Datetime.from_string('2013-02-26 08:00:00'), Datetime.from_string('2013-02-26 09:00:00')))

        td = timedelta()
        for item in res:
            td += item[1] - item[0]
        self.assertEqual(seconds(td) / 3600.0, 40.0)

    def test_calendar_hours_scheduling_forward_leaves_resource(self):
        res = self.calendar.schedule_hours(
            40, day_dt=Datetime.from_string('2013-02-12 09:00:00'),
            compute_leaves=True, resource_id=self.resource1_id
        )
        self.assertEqual(res[0], (Datetime.from_string('2013-02-12 09:00:00'), Datetime.from_string('2013-02-12 16:00:00')))
        self.assertEqual(res[1], (Datetime.from_string('2013-02-15 08:00:00'), Datetime.from_string('2013-02-15 13:00:00')))
        self.assertEqual(res[2], (Datetime.from_string('2013-02-15 16:00:00'), Datetime.from_string('2013-02-15 23:00:00')))
        self.assertEqual(res[3], (Datetime.from_string('2013-02-19 08:00:00'), Datetime.from_string('2013-02-19 09:00:00')))
        self.assertEqual(res[4], (Datetime.from_string('2013-02-19 12:00:00'), Datetime.from_string('2013-02-19 16:00:00')))
        self.assertEqual(res[5], (Datetime.from_string('2013-02-22 08:00:00'), Datetime.from_string('2013-02-22 09:00:00')))
        self.assertEqual(res[6], (Datetime.from_string('2013-02-22 16:00:00'), Datetime.from_string('2013-02-22 23:00:00')))
        self.assertEqual(res[7], (Datetime.from_string('2013-03-01 11:30:00'), Datetime.from_string('2013-03-01 13:00:00')))
        self.assertEqual(res[8], (Datetime.from_string('2013-03-01 16:00:00'), Datetime.from_string('2013-03-01 22:30:00')))

        td = timedelta()
        for item in res:
            td += item[1] - item[0]
        self.assertEqual(seconds(td) / 3600.0, 40.0)

    def test_calendar_days_scheduling(self):
        res = self.calendar.schedule_days_get_date(5, day_date=Datetime.from_string('2013-02-12 09:08:07') )
        self.assertEqual(res.date(), Datetime.from_string('2013-02-26 00:00:00').date(), 'resource_calendar: wrong days scheduling')
        res = self.calendar.schedule_days_get_date(-2, day_date=Datetime.from_string('2013-02-12 09:08:07') )
        self.assertEqual(res.date(), Datetime.from_string('2013-02-08 00:00:00').date(), 'resource_calendar: wrong days scheduling')

        res = self.calendar.schedule_days_get_date(
            5, day_date=Datetime.from_string('2013-02-12 09:08:07'),
            compute_leaves=True, resource_id=self.resource1_id)
        self.assertEqual(res.date(), Datetime.from_string('2013-03-01 00:00:00').date(), 'resource_calendar: wrong days scheduling')

    def test_calendar_days_scheduling_without_calendar(self):
        # Without calendar, should only count days -> 12 -> 16, 5 days with default intervals
        res = self.env['resource.calendar'].with_context(tz='UTC').schedule_days_get_date(5, day_date=Datetime.from_string('2013-02-12 09:08:07'), default_interval=(8, 16))
        self.assertEqual(res, Datetime.from_string('2013-02-16 16:00:00'), 'resource_calendar: wrong days scheduling')


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

        self._days = [
            date.fromordinal(o)
            for o in xrange(
                WAR_START.toordinal(),
                WAR_END.toordinal() + 1
            )
        ]

    def test_no_calendar(self):
        """ If a resource has no resource calendar, they don't work """
        r = self.env['resource.resource'].create({
            'name': "NoCalendar"
        })

        self.assertEqual(
            [],
            list(r._iter_work_days(WAR_START, WAR_END)),
        )

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
            list(r._iter_work_days(WAR_START, WAR_END))
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
        self.assertEqual(days, list(r1._iter_work_days(WAR_START, WAR_END)))
        self.assertEqual(days, list(r2._iter_work_days(WAR_START, WAR_END)))

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
        self.assertEqual(weekdays, list(r1._iter_work_days(WAR_START, WAR_END)))
        self.assertEqual([
            d for d in weekdays if d < date(1932, 11, 9) or d > date(1932, 11, 12)],
            list(r2._iter_work_days(WAR_START, WAR_END))
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
            list(r._iter_work_days(WAR_START, WAR_END))
        )

        # _is_work_day is built on _iter_work_days, but it's probably a good
        # idea to ensure it does do what it should
        self.assertTrue(r._is_work_day(date(1932, 11, 8)))
        self.assertTrue(r._is_work_day(date(1932, 11, 14)))
        self.assertTrue(r._is_work_day(date(1932, 12, 1)))

        self.assertFalse(r._is_work_day(date(1932, 11, 11)))  # global leave
        self.assertFalse(r._is_work_day(date(1932, 11, 13)))  # sun
        self.assertFalse(r._is_work_day(date(1932, 11, 19)))  # sat
        self.assertFalse(r._is_work_day(date(1932, 11, 20)))  # sun
        self.assertFalse(r._is_work_day(date(1932, 12, 6)))  # personal leave

def seconds(td):
    assert isinstance(td, timedelta)

    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.**6
