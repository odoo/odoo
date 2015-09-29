# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from openerp.tests import common


class TestResourceCommon(common.TransactionCase):

    def setUp(self):
        super(TestResourceCommon, self).setUp()
        cr, uid = self.cr, self.uid
        self.context = context = dict(tz='UTC')

        self.registry('res.users').write(cr, uid, uid, {'tz': 'UTC'}, context=context)

        # Usefull models
        self.resource_resource = self.registry('resource.resource')
        self.resource_calendar = self.registry('resource.calendar')
        self.resource_attendance = self.registry('resource.calendar.attendance')
        self.resource_leaves = self.registry('resource.calendar.leaves')

        # Some demo data
        self.date1 = datetime.strptime('2013-02-12 09:08:07', '%Y-%m-%d %H:%M:%S')  # weekday() returns 1, isoweekday() returns 2
        self.date2 = datetime.strptime('2013-02-15 10:11:12', '%Y-%m-%d %H:%M:%S')  # weekday() returns 4, isoweekday() returns 5
        # Leave1: 19/02/2013, from 9 to 12, is a day 1
        self.leave1_start = datetime.strptime('2013-02-19 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.leave1_end = datetime.strptime('2013-02-19 12:00:00', '%Y-%m-%d %H:%M:%S')
        # Leave2: 22/02/2013, from 9 to 15, is a day 4
        self.leave2_start = datetime.strptime('2013-02-22 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.leave2_end = datetime.strptime('2013-02-22 15:00:00', '%Y-%m-%d %H:%M:%S')
        # Leave3: 25/02/2013 (day0) -> 01/03/2013 (day4)
        self.leave3_start = datetime.strptime('2013-02-25 13:00:00', '%Y-%m-%d %H:%M:%S')
        self.leave3_end = datetime.strptime('2013-03-01 11:30:00', '%Y-%m-%d %H:%M:%S')

        # Resource data
        # Calendar working days: 1 (8-16 -> 8hours), 4 (8-13, 16-23 -> 12hours)
        self.calendar_id = self.resource_calendar.create(
            cr, uid, {
                'name': 'TestCalendar',
            }, context=context
        )
        self.att1_id = self.resource_attendance.create(
            cr, uid, {
                'name': 'Att1',
                'dayofweek': '1',
                'hour_from': 8,
                'hour_to': 16,
                'calendar_id': self.calendar_id,
            }, context=context
        )
        self.att2_id = self.resource_attendance.create(
            cr, uid, {
                'name': 'Att2',
                'dayofweek': '4',
                'hour_from': 8,
                'hour_to': 13,
                'calendar_id': self.calendar_id,
            }, context=context
        )
        self.att3_id = self.resource_attendance.create(
            cr, uid, {
                'name': 'Att3',
                'dayofweek': '4',
                'hour_from': 16,
                'hour_to': 23,
                'calendar_id': self.calendar_id,
            }, context=context
        )
        self.resource1_id = self.resource_resource.create(
            cr, uid, {
                'name': 'TestResource1',
                'resource_type': 'user',
                'time_efficiency': 150.0,
                'calendar_id': self.calendar_id,
            }, context=context
        )
        self.leave1_id = self.resource_leaves.create(
            cr, uid, {
                'name': 'GenericLeave',
                'calendar_id': self.calendar_id,
                'date_from': self.leave1_start,
                'date_to': self.leave1_end,
            }, context=context
        )
        self.leave2_id = self.resource_leaves.create(
            cr, uid, {
                'name': 'ResourceLeave',
                'calendar_id': self.calendar_id,
                'resource_id': self.resource1_id,
                'date_from': self.leave2_start,
                'date_to': self.leave2_end,
            }, context=context
        )
        self.leave3_id = self.resource_leaves.create(
            cr, uid, {
                'name': 'ResourceLeave2',
                'calendar_id': self.calendar_id,
                'resource_id': self.resource1_id,
                'date_from': self.leave3_start,
                'date_to': self.leave3_end,
            }, context=context
        )
        # Some browse data
        self.calendar = self.resource_calendar.browse(cr, uid, self.calendar_id, context=context)
