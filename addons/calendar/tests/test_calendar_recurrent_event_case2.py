# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.addons.calendar.models.calendar_event import calendar_id2real_id


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
            'day': 0.0,
            'duration': 1.0,
            'final_date': '2011-04-30',
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
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2011-05-13')
        ])
        self.assertEqual(meetings_count, 10, 'Recurrent weekly meetings are not created !')

    def test_recurrent_meeting3(self):
        #I want to schedule a meeting every month for Sprint review.
        self.calendar_event_sprint_review = self.CalendarEvent.create({
            'count': 12,
            'start': '2011-04-01 12:01:00',
            'stop': '2011-04-01 13:01:00',
            'day': 1,
            'duration': 1.0,
            'name': 'Sprint Review',
            'recurrency': True,
            'rrule_type': 'monthly'
        })

        # I search for all the recurrent monthly meetings.
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-01'), ('stop', '<=', '2012-05-13')
        ])
        self.assertEqual(meetings_count, 12, 'Recurrent weekly meetings are not created !')

        # I change name of my monthly Sprint Review meeting.
        idval = '%d-%s' % (self.calendar_event_sprint_review.id, '20110901130100')
        self.CalendarEvent.browse(idval).write({'name': 'Sprint Review for google modules'})

        # I check whether all the records are edited or not.
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([
            ('start', '>=', '2011-03-01'), ('stop', '<=', '2012-05-13')
        ])
        for meeting in meetings:
            self.assertEqual(meeting.name, 'Sprint Review for google modules', 'Name not changed for id: %s' % meeting.id)

        # I detach first occurrence to check it is not modified by changing recurrent event.
        min(meetings, key=lambda m: m.start).detach_recurring_event()

        # I change description of my weekly meeting Review code with programmer.
        idval = '%d-%s' % (self.calendar_event_sprint_review.id, '20110425124700')
        self.CalendarEvent.browse(idval).write({'description': 'Review code of the module: sync_google_calendar.'})

        # I check that detached event has not been edited.
        detached_meeting = self.CalendarEvent.search([('recurrent_id', '=', self.calendar_event_sprint_review.id)])
        self.assertEqual(detached_meeting.description, False, 'Detached event description changed for id: %s' % meeting.id)

        # I verify wether I find an event by date range when subsequent to a detached one.
        last_meeting = max(meetings, key=lambda m: m.start)
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([
            ('start', '<=', str(last_meeting.stop)), ('stop', '>=', str(last_meeting.start))
        ])
        self.assertEqual(meetings.id, last_meeting.id, 'Last event should be found searching it by date range')

        # I update the description of two meetings, and check that both have been updated
        self.calendar_event_sprint_review.write({'description': "Some description"})
        self.assertEqual(self.calendar_event_sprint_review.description, "Some description", "Event %d has not been updated" % self.calendar_event_sprint_review.id)

    def test_recurrent_meeting4(self):
        # I create a weekly meeting till a particular end date.
        self.CalendarEvent.create({
            'start': '2017-01-22 11:47:00',
            'stop': '2017-01-22 12:47:00',
            'day': 0.0,
            'duration': 1.0,
            'final_date': '2017-06-30',
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

        # I search for a recurrent weekly meetings that take place at a given date.
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '<=', '2017-01-24'), ('stop', '>=', '2017-01-24'), ('name', '=', 'Review code with programmer')
        ])
        self.assertEqual(meetings_count, 1, 'Recurrent weekly meetings are not found using date filter !')

        # I search for a recurrent weekly meetings that take place at a given date and time.
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '<=', '2017-01-24 11:55:00'), ('stop', '>=', '2017-01-24 11:55:00'), ('name', '=', 'Review code with programmer')
        ])
        self.assertEqual(meetings_count, 1, 'Recurrent weekly meetings are not found using time filter !')

        # I search using the filter 'start date is set'
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '!=', False), ('stop', '>=', '2017-06-30 11:55:00'), ('name', '=', 'Review code with programmer')
        ])
        self.assertEqual(meetings_count, 1, "Last recurrent weekly meetings are not found using 'is set' filter !")

        # I search for a recurrent weekly meetings that take place at a given date and time.
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '<=', '2017-01-24 11:55:00'), ('stop', '>=', '2017-01-24 15:55:00')
        ])
        self.assertEqual(meetings_count, 0, 'Too late recurrent meetings are found using time filter !')

        # I search using a start filter but no stop
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2017-06-30 08:00:00'), ('name', '=', 'Review code with programmer')
        ])
        self.assertEqual(meetings_count, 1, "Last recurrent weekly meetings are not found without stop filter !")

    def test_recurrent_meeting5(self):
        # I create a recurrent event and I check if the virtual_id are correct
        self.CalendarEvent.create({
            'count': 5,
            'start': '2012-04-13 11:00:00',
            'stop': '2012-04-13 12:00:00',
            'duration': 1.0,
            'name': 'Test Meeting',
            'recurrency': True,
            'rrule_type': 'daily'
        })
        # I search for the first recurrent meeting
        meeting = self.CalendarEvent.with_context({'virtual_id': True}).search([
            ('start', '=', '2012-04-13 11:00:00'), ('stop', '=', '2012-04-13 12:00:00')
        ])
        virutal_dates = calendar_id2real_id(meeting.id, with_date=True)

        # virtual_dates are used by the calendar view and I check if the start date for the first virtual event is correct.
        self.assertEqual(virutal_dates[1], '2012-04-13 11:00:00', "The virtual event doesn't have the correct start date !")

        # virtual_dates are used by the calendar view and I check if the stop date for the first virtual event is correct.
        self.assertEqual(virutal_dates[2], '2012-04-13 12:00:00', "The virtual event doesn't have the correct stop date !")

    def test_recurrent_meeting6(self):
        ev = self.CalendarEvent.create({
            'name': 'Rec1',
            'start': '2018-06-28 11:00:00',
            'stop': '2018-06-28 12:00:00',
            'day': 0.0,
            'duration': 1.0,
            'count': ' 2',
            'end_type': 'count',
            'fr': True,
            'recurrency': True,
            'allday': False,
            'rrule_type': 'weekly'
        })
        #event 2018-07-06 and 2018-06-29
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([
            '|', '&', ('start', '>=', '2018-06-30 00:00:00'), ('start', '<=', '2018-06-30 23:59:59'), ('allday', '=', True)
        ])
        base_ids = [calendar_id2real_id(meeting.id, with_date=False) for meeting in meetings]
        self.assertNotIn(ev.id, base_ids, "Event does not match the domain")

        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([
            '|', '&', ('start', '>=', '2018-06-29 00:00:00'), ('start', '<=', '2018-06-29 23:59:59'), ('allday', '=', True)
        ])
        base_ids = [calendar_id2real_id(meeting.id, with_date=False) for meeting in meetings]
        self.assertIn(ev.id, base_ids, "Event does match the domain")
