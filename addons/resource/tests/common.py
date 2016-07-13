# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Datetime
from odoo.tests.common import TransactionCase


class TestResourceCommon(TransactionCase):

    def setUp(self):
        super(TestResourceCommon, self).setUp()
        self.context = context = dict(tz='UTC')

        self.env['res.users'].browse(self.env.uid).with_context(context).write({'tz': 'UTC'})

        # Usefull models
        self.Resource = self.env['resource.resource']
        self.ResourceCalendar = self.env['resource.calendar']
        self.ResourceAttendance = self.env['resource.calendar.attendance']
        self.ResourceLeaves = self.env['resource.calendar.leaves']

        # Some demo data
        self.date1 = Datetime.from_string('2013-02-12 09:08:07')  # weekday() returns 1, isoweekday() returns 2
        self.date2 = Datetime.from_string('2013-02-15 10:11:12')  # weekday() returns 4, isoweekday() returns 5
        # Leave1: 19/02/2013, from 9 to 12, is a day 1
        self.leave1_start = Datetime.from_string('2013-02-19 09:00:00')
        self.leave1_end = Datetime.from_string('2013-02-19 12:00:00')
        # Leave2: 22/02/2013, from 9 to 15, is a day 4
        self.leave2_start = Datetime.from_string('2013-02-22 09:00:00')
        self.leave2_end = Datetime.from_string('2013-02-22 15:00:00')
        # Leave3: 25/02/2013 (day0) -> 01/03/2013 (day4)
        self.leave3_start = Datetime.from_string('2013-02-25 13:00:00')
        self.leave3_end = Datetime.from_string('2013-03-01 11:30:00')

        # Resource data
        # Calendar working days: 1 (8-16 -> 8hours), 4 (8-13, 16-23 -> 12hours)
        self.calendar = self.ResourceCalendar.with_context(context).create(
            {
                'name': 'TestCalendar',
            }
        )
        self.att1_id = self.ResourceAttendance.with_context(context).create(
            {
                'name': 'Att1',
                'dayofweek': '1',
                'hour_from': 8,
                'hour_to': 16,
                'calendar_id': self.calendar.id,
            }
        ).id
        self.att2_id = self.ResourceAttendance.with_context(context).create(
            {
                'name': 'Att2',
                'dayofweek': '4',
                'hour_from': 8,
                'hour_to': 13,
                'calendar_id': self.calendar.id,
            }
        ).id
        self.att3_id = self.ResourceAttendance.with_context(context).create(
            {
                'name': 'Att3',
                'dayofweek': '4',
                'hour_from': 16,
                'hour_to': 23,
                'calendar_id': self.calendar.id,
            }
        ).id
        self.resource1_id = self.Resource.with_context(context).create(
            {
                'name': 'TestResource1',
                'resource_type': 'user',
                'time_efficiency': 150.0,
                'calendar_id': self.calendar.id,
            }
        ).id
        self.leave1_id = self.ResourceLeaves.with_context(context).create(
            {
                'name': 'GenericLeave',
                'calendar_id': self.calendar.id,
                'date_from': self.leave1_start,
                'date_to': self.leave1_end,
            }
        ).id
        self.leave2_id = self.ResourceLeaves.with_context(context).create(
            {
                'name': 'ResourceLeave',
                'calendar_id': self.calendar.id,
                'resource_id': self.resource1_id,
                'date_from': self.leave2_start,
                'date_to': self.leave2_end,
            }
        ).id
        self.leave3_id = self.ResourceLeaves.with_context(context).create(
            {
                'name': 'ResourceLeave2',
                'calendar_id': self.calendar.id,
                'resource_id': self.resource1_id,
                'date_from': self.leave3_start,
                'date_to': self.leave3_end,
            }
        ).id
