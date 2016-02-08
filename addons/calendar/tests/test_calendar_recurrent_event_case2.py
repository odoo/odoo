# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common


class TestRecurrentEvent(common.TransactionCase):

    def setUp(self):
        super(TestRecurrentEvent, self).setUp()

        self.CalendarEvent = self.env['calendar.event']

    def test_recurrent_meeting1(self):
        # In order to test recurrent meetings in Odoo, I create meetings with different recurrency using different test cases.
        # I create a recurrent meeting with daily recurrency and fixed amount of time.
        self.CalendarEvent.create({
            'count': 5,
            'start': '2011-04-13 11:04:00',
            'stop': '2011-04-13 12:04:00',
            'duration': 1.0,
            'name': 'Test Meeting',
            'recurrency': True,
            'recurrent_id': 0,
            'rrule_type': 'daily'})

        # I search for all the recurrent meetings.
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([('start', '>=', '2011-03-13'), ('stop', '<=', '2011-05-13')])
        self.assertEqual(len(meetings), 5, 'Recurrent daily meetings are not created !')

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
            'recurrent_id': 0,
            'rrule_type': 'weekly'})

        # I search for all the recurrent weekly meetings.
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([('start', '>=', '2011-03-13'), ('stop', '<=', '2011-05-13')])
        self.assertEqual(len(meetings), 10, 'Recurrent weekly meetings are not created !')

    def test_recurrent_meeting3(self):
        #I want to schedule a meeting every month for Sprint review.
        calendar_event_sprint_review = self.CalendarEvent.create({
            'count': 12,
            'start': '2011-04-01 12:01:00',
            'stop': '2011-04-01 13:01:00',
            'day': 1,
            'duration': 1.0,
            'name': 'Sprint Review',
            'recurrency': True,
            'recurrent_id': 0.0,
            'rrule_type': 'monthly'})

        # I search for all the recurrent monthly meetings.|
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([('start', '>=', '2011-03-01'), ('stop', '<=', '2012-05-13')])
        self.assertEqual(len(meetings), 12, 'Recurrent weekly meetings are not created !')

        # I change name of my monthly Sprint Review meeting.
        idval = '%d-%s' % (calendar_event_sprint_review, '20110901130100')
        self.CalendarEvent.browse(idval).write({'name': 'Sprint Review for google modules'})

        # I check whether all the records are edited or not.
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([('start', '>=', '2011-03-01'), ('stop', '<=', '2012-05-13')])
        for meeting in meetings:
            self.assertEqual(meeting.name, 'Sprint Review for google modules', 'Name not changed for id: %s' % meeting.id)

        # I change description of my weekly meeting Review code with programmer.
        idval = '%d-%s' % (calendar_event_sprint_review, '20110425124700')
        self.CalendarEvent.browse(idval).write({'description': 'Review code of the module: sync_google_calendar.'})

        # I check whether that all the records of this recurrence has been edited.
        meetings = self.CalendarEvent.search([('recurrent_id', '=', calendar_event_sprint_review.id)])
        for meeting in meetings:
            self.assertEqual(meeting.description, 'Review code of the module: sync_google_calendar.', 'Description not changed for id: %s' % meeting.id)
