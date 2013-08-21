# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.resource.tests.common import TestResourceCommon


class TestResource(TestResourceCommon):

    def test_00_intervals(self):
        intervals = [
            (
                datetime.strptime('2013-02-04 09:00:00', '%Y-%m-%d %H:%M:%S'),
                datetime.strptime('2013-02-04 11:00:00', '%Y-%m-%d %H:%M:%S')
            ), (
                datetime.strptime('2013-02-04 08:00:00', '%Y-%m-%d %H:%M:%S'),
                datetime.strptime('2013-02-04 12:00:00', '%Y-%m-%d %H:%M:%S')
            ), (
                datetime.strptime('2013-02-04 11:00:00', '%Y-%m-%d %H:%M:%S'),
                datetime.strptime('2013-02-04 14:00:00', '%Y-%m-%d %H:%M:%S')
            ), (
                datetime.strptime('2013-02-04 17:00:00', '%Y-%m-%d %H:%M:%S'),
                datetime.strptime('2013-02-04 21:00:00', '%Y-%m-%d %H:%M:%S')
            ), (
                datetime.strptime('2013-02-03 08:00:00', '%Y-%m-%d %H:%M:%S'),
                datetime.strptime('2013-02-03 10:00:00', '%Y-%m-%d %H:%M:%S')
            ), (
                datetime.strptime('2013-02-04 18:00:00', '%Y-%m-%d %H:%M:%S'),
                datetime.strptime('2013-02-04 19:00:00', '%Y-%m-%d %H:%M:%S')
            )
        ]

        # Test: interval cleaning
        result = self.resource_calendar.interval_clean(intervals)
        self.assertEqual(len(result), 3, 'resource_calendar: wrong interval cleaning')
        # First interval: 03, unchanged
        self.assertEqual(result[0][0], datetime.strptime('2013-02-03 08:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong interval cleaning')
        self.assertEqual(result[0][1], datetime.strptime('2013-02-03 10:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong interval cleaning')
        # Second intreval: 04, 08-14, combining 08-12 and 11-14, 09-11 being inside 08-12
        self.assertEqual(result[1][0], datetime.strptime('2013-02-04 08:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong interval cleaning')
        self.assertEqual(result[1][1], datetime.strptime('2013-02-04 14:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong interval cleaning')
        # Third interval: 04, 17-21, 18-19 being inside 17-21
        self.assertEqual(result[2][0], datetime.strptime('2013-02-04 17:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong interval cleaning')
        self.assertEqual(result[2][1], datetime.strptime('2013-02-04 21:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong interval cleaning')

        # Test: disjoint removal
        working_interval = (datetime.strptime('2013-02-04 08:00:00', '%Y-%m-%d %H:%M:%S'), datetime.strptime('2013-02-04 18:00:00', '%Y-%m-%d %H:%M:%S'))
        result = self.resource_calendar.interval_remove_leaves(working_interval, intervals)
        self.assertEqual(len(result), 1, 'resource_calendar: wrong leave removal from interval')
        # First interval: 04, 14-17
        self.assertEqual(result[0][0], datetime.strptime('2013-02-04 14:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong leave removal from interval')
        self.assertEqual(result[0][1], datetime.strptime('2013-02-04 17:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong leave removal from interval')

    def test_10_calendar_basics(self):
        """ Testing basic method of resource.calendar """
        cr, uid = self.cr, self.uid

        # --------------------------------------------------
        # Test1: get_next_day
        # --------------------------------------------------

        # Test: next day: next day after day1 is day4
        date = self.resource_calendar.get_next_day(cr, uid, self.calendar_id, day_date=self.date1)
        self.assertEqual(date, self.date2, 'resource_calendar: wrong next day computing')

        # Test: next day: next day after day4 is (day1+7)
        date = self.resource_calendar.get_next_day(cr, uid, self.calendar_id, day_date=self.date2)
        self.assertEqual(date, self.date1 + relativedelta(days=7), 'resource_calendar: wrong next day computing')

        # Test: next day: next day after day4+1 is (day1+7)
        date = self.resource_calendar.get_next_day(cr, uid, self.calendar_id, day_date=self.date2 + relativedelta(days=1))
        self.assertEqual(date, self.date1 + relativedelta(days=7), 'resource_calendar: wrong next day computing')

        # Test: next day: next day after day1-1 is day1
        date = self.resource_calendar.get_next_day(cr, uid, self.calendar_id, day_date=self.date1 + relativedelta(days=-1))
        self.assertEqual(date, self.date1, 'resource_calendar: wrong next day computing')

        # --------------------------------------------------
        # Test2: get_previous_day
        # --------------------------------------------------

        # Test: previous day: previous day before day1 is (day4-7)
        date = self.resource_calendar.get_previous_day(cr, uid, self.calendar_id, day_date=self.date1)
        self.assertEqual(date, self.date2 + relativedelta(days=-7), 'resource_calendar: wrong previous day computing')

        # Test: previous day: previous day before day4 is day1
        date = self.resource_calendar.get_previous_day(cr, uid, self.calendar_id, day_date=self.date2)
        self.assertEqual(date, self.date1, 'resource_calendar: wrong previous day computing')

        # Test: previous day: previous day before day4+1 is day4
        date = self.resource_calendar.get_previous_day(cr, uid, self.calendar_id, day_date=self.date2 + relativedelta(days=1))
        self.assertEqual(date, self.date2, 'resource_calendar: wrong previous day computing')

        # Test: previous day: previous day before day1-1 is (day4-7)
        date = self.resource_calendar.get_previous_day(cr, uid, self.calendar_id, day_date=self.date1 + relativedelta(days=-1))
        self.assertEqual(date, self.date2 + relativedelta(days=-7), 'resource_calendar: wrong previous day computing')

    def test_20_calendar_working_intervals(self):
        """ Testing working intervals computing method of resource.calendar """
        cr, uid = self.cr, self.uid

        # Test: day0 without leaves: 1 interval
        intervals = self.resource_calendar.get_working_intervals_of_day(cr, uid, self.calendar_id, day_date=self.date1)
        self.assertEqual(len(intervals), 1, 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[0][0], datetime.strptime('2013-02-12 08:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[0][1], datetime.strptime('2013-02-12 16:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')

        # Test: day3 without leaves: 2 interval
        intervals = self.resource_calendar.get_working_intervals_of_day(cr, uid, self.calendar_id, day_date=self.date2)
        self.assertEqual(len(intervals), 2, 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[0][0], datetime.strptime('2013-02-15 08:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[0][1], datetime.strptime('2013-02-15 13:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[1][0], datetime.strptime('2013-02-15 16:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[1][1], datetime.strptime('2013-02-15 23:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')

        # Test: day0 with leaves outside range: 1 interval
        intervals = self.resource_calendar.get_working_intervals_of_day(cr, uid, self.calendar_id, day_date=self.date1, compute_leaves=True)
        self.assertEqual(len(intervals), 1, 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[0][0], datetime.strptime('2013-02-12 08:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[0][1], datetime.strptime('2013-02-12 16:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')

        # Test: day0 with leaves: 2 intrevals because of leave between 9 ans 12
        intervals = self.resource_calendar.get_working_intervals_of_day(cr, uid, self.calendar_id, day_date=self.date1 + relativedelta(days=7), compute_leaves=True)
        self.assertEqual(len(intervals), 2, 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[0][0], datetime.strptime('2013-02-19 08:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[0][1], datetime.strptime('2013-02-19 09:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[1][0], datetime.strptime('2013-02-19 12:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')
        self.assertEqual(intervals[1][1], datetime.strptime('2013-02-19 16:00:00', '%Y-%m-%d %H:%M:%S'), 'resource_calendar: wrong working intervals')

    def test_40_calendar_schedule_days(self):
        """ Testing calendar days scheduling """
        cr, uid = self.cr, self.uid

        print '---------------'
        res = self.resource_calendar.schedule_days(cr, uid, self.calendar_id, 5, date=self.date1)
        print res

        # --------------------------------------------------
        # Misc
        # --------------------------------------------------

        # Without calendar, should only count days
        print '---------------'
        res = self.resource_calendar.schedule_days(cr, uid, None, 5, date=self.date1)
        print res

    # @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    # def test_20_calendar(self):
    #     """ Testing calendar and time computation """
    #     cr, uid = self.cr, self.uid

    #     wh = self.resource_calendar.get_working_hours_of_date(cr, uid, self.calendar_id, day_date=self.date1)
    #     self.assertEqual(wh, 8, 'cacamou')

    #     wh = self.resource_calendar.get_working_hours_of_date(cr, uid, self.calendar_id, day_date=self.date2+relativedelta(days=7))
    #     self.assertEqual(wh, 12, 'cacamou')

    #     # print '---------------------'
    #     # print self.date1
    #     # res = self.resource_calendar.interval_min_get(cr, uid, self.calendar_id, self.date1, 40, resource=False)
    #     # print res

    #     print '----------------------'
    #     res = self.resource_calendar.schedule_hours(cr, uid, self.calendar_id, 40, start_datetime=self.date1)
    #     print res
    #     print '----------------------'
    #     # print self.date1
    #     # res = self.resource_calendar.interval_get(cr, uid, self.calendar_id, self.date1, 40, resource=False, byday=True)
    #     # print res
