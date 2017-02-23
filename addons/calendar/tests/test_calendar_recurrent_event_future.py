# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestRecurrentEvent(common.TransactionCase):

    def setUp(self):
        super(TestRecurrentEvent, self).setUp()

        self.CalendarEvent = self.env['calendar.event']

    def test_recurrent_meeting_future_update(self):
        # In order to test recurrent meetings in Odoo, I create meetings with different recurrency using different test cases.
        # I create a recurrent meeting with daily recurrency and fixed amount of time.
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
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([
            ('start', '>=', '2011-03-01'), ('stop', '<=', '2012-05-13')
        ])

        # I break the event for the future
        future_events = meetings[9].action_future_recurring_event()
        # Write in the event returned by the action
        self.CalendarEvent.browse(future_events.get('res_id')).write({
            'duration': 2.0
        })
        previous_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13'), ('duration', '=', 1.0)
        ])
        all_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13')
        ])
        # Change the duration of the future event to 2 hours
        future_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13'), ('duration', '=', 2.0)
        ])
        # Check the number of past events.
        self.assertEqual(previous_count, 2, 'Wrong number of past events !')
        # We should have the same amount of events than before the split.
        self.assertEqual(all_count, 12, 'Wrong number of global events !')
        # The new recurring event should have virtual events equals to total events - past events.
        self.assertEqual(future_count, 10, 'Wrong number of future events !')

    def test_recurrent_meeting_all_update(self):
        # In order to test recurrent meetings in Odoo, I create meetings with different recurrency using different test cases.
        # I create a recurrent meeting with daily recurrency and fixed amount of time.
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
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([
            ('start', '>=', '2011-03-01'), ('stop', '<=', '2012-05-13')
        ])

        # Run the 'all events update action for an arbitrary event'
        all_events = meetings[9].action_all_recurring_event()
        # Write in the event returned by the action
        self.CalendarEvent.browse(all_events.get('res_id')).write({
            'duration': 2.0
        })
        previous_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13'), ('duration', '=', 1.0)
        ])
        all_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13')
        ])
        # Change the duration of the all event to 2 hours
        future_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13'), ('duration', '=', 2.0)
        ])
        # Check the number of past events. There shouldn't be one because they should have been updated to 2 hours duration.
        self.assertEqual(previous_count, 0, 'Wrong number of past events !')
        # We should have the same amount of events than before the modification.
        self.assertEqual(all_count, 12, 'Wrong number of global events !')
        # The count of recurring events modified should be the same than all events. We updated them to 2 hours duration.
        self.assertEqual(future_count, 12, 'Wrong number of future events !')

    def test_recurrent_meeting_one_update(self):
        # In order to test recurrent meetings in Odoo, I create meetings with different recurrency using different test cases.
        # I create a recurrent meeting with daily recurrency and fixed amount of time.
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
        meetings = self.CalendarEvent.with_context({'virtual_id': True}).search([
            ('start', '>=', '2011-03-01'), ('stop', '<=', '2012-05-13')
        ])

        # Run the 'all events update action for an arbitrary event'
        unique_events = meetings[9].action_detach_recurring_event()
        # Write in the event returned by the action
        self.CalendarEvent.browse(unique_events.get('res_id')).write({
            'duration': 2.0
        })
        previous_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13'), ('duration', '=', 1.0)
        ])
        all_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13')
        ])
        # Change the duration of the event to 2 hours
        future_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2012-05-13'), ('duration', '=', 2.0)
        ])
        # Check the number of past events. There should be number of initial events - the one we edited
        self.assertEqual(previous_count, 11, 'Wrong number of past events !')
        # We should have the same amount of total events than before the modification.
        self.assertEqual(all_count, 12, 'Wrong number of global events !')
        # The count of event with a duration of two hours should be one (the one we edited)
        self.assertEqual(future_count, 1, 'Wrong number of future events !')
