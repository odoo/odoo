# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestRecurrentEvent(common.TransactionCase):

    def setUp(self):
        super(TestRecurrentEvent, self).setUp()

        self.CalendarEvent = self.env['calendar.event']

    def test_recurrent_meeting1(self):
        # In order to test recurrent meetings in Odoo, I create meetings with different recurrence using different test cases.
        # I create a recurrent meeting with daily recurrence and fixed amount of time.
        self.CalendarEvent.create({
            'count': 5,
            'start': '2011-04-13 11:04:00',
            'stop': '2011-04-13 12:04:00',
            'duration': 1.0,
            'name': 'Test Meeting',
            'recurrency': True,
            'rrule_type': 'daily'
        })
        # I search for all the recurrent meetings
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2011-05-13')
        ])
        self.assertEqual(meetings_count, 5, 'Recurrent daily meetings are not created !')

    def test_recurrent_meeting2(self):
        # I create a weekly meeting till a particular end date.
        self.CalendarEvent.create({
            'start': '2011-04-18 11:47:00',
            'stop': '2011-04-18 12:47:00',
            'day': 1,
            'duration': 1.0,
            'until': '2011-04-30',
            'end_type': 'end_date',
            'fr': True,
            'mo': True,
            'th': True,
            'tu': True,
            'we': True,
            'name': 'Review code with programmer',
            'recurrency': True,
            'rrule_type': 'weekly'
        })

        # I search for all the recurrent weekly meetings.
        meetings_count = self.CalendarEvent.search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2011-05-13')
        ])
        self.assertEqual(meetings_count, 10, 'Recurrent weekly meetings are not created !')
