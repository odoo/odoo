# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.tests import common


class TestCalendar(common.TransactionCase):

    def setUp(self):
        super(TestCalendar, self).setUp()

        self.CalendarEvent = self.env['calendar.event']
        #In Order to test calendar, I will first create One Simple Event with real data
        self.calendar_event = self.CalendarEvent.create({
            'privacy': 'private',
            'start': '2011-04-30 16:00:00',
            'stop': '2011-04-30 18:30:00',
            'description': 'The Technical Presentation will cover following topics:\n* Creating OpenERP class\n* Views\n* Wizards\n* Workflows',
            'duration': 2.5,
            'location': 'Odoo S.A.',
            'name': 'Technical Presentation'})

    def test_calender_event(self):
        #Now I will set recurrence for this event to occur monday and friday of week
        data = {
            'fr': 1,
            'mo': 1,
            'interval': 1,
            'rrule_type': 'weekly',
            'end_type': 'end_date',
            'final_date': '2011-05-31 00:00:00',
            'recurrency': True}

        self.calendar_event.write(data)

        # In order to check that recurrent events are views successfully in calendar view, I will open calendar view of events|
        self.CalendarEvent.fields_view_get(False, 'calendar')

        #In order to check that recurrent events are views successfully in calendar view, I will search for one of the recurrent event and count the number of events
        rec_events = self.CalendarEvent.with_context({'virtual_id': True}).search([('start', '>=', '2011-04-30 16:00:00'), ('start', '<=', '2011-05-31 00:00:00')])
        self.assertEqual(len(rec_events), 9, 'Wrong number of events found')

        #Now I move a virtual event, to see that a real event is well created and depending from the native recurrence
        before = self.CalendarEvent.with_context({'virtual_id': False}).search([('start', '>=', '2011-04-30 16:00:00'), ('start', '<=', '2011-05-31 00:00:00')])

        # We start by detach the event
        newevent = rec_events[1]._detach_one_event()
        newevent.with_context({'virtual_id': True}).write({'name': 'New Name', 'recurrency': True})
        after = self.CalendarEvent.with_context({'virtual_id': False}).search([('start', '>=', '2011-04-30 16:00:00'), ('start', '<=', '2011-05-31 00:00:00')])
        self.assertEqual(len(after), len(before)+1, 'Wrong number of events found, after to have moved a virtual event')
        new_event = after - before
        self.assertEqual(new_event.recurrent_id, before.id, 'Recurrent_id not correctly passed to the new event')

        # Now I will make All day event and test it
        self.CalendarEvent.create({
            'allday': 1,
            'privacy': 'confidential',
            'start': '2011-04-30 00:00:00',
            'stop': '2011-04-30 00:00:00',
            'description': 'All day technical test',
            'location': 'School',
            'name': 'All day test event'})

        # In order to check reminder I will first create reminder
        res_alarm_day_before_event_starts = self.env['calendar.alarm'].create({
            'name': '1 Day before event starts',
            'duration': 1,
            'interval': 'days',
            'type': 'notification'})

        # Now I will assign this reminder to all day event|
        self.CalendarEvent.write({'alarm_ids': [(6, 0, [res_alarm_day_before_event_starts.id])]})

        # I create a recuring rule for my event

        calendar_event_sprint_review = self.CalendarEvent.create({
            'name': 1,
            'start': time.strftime('%Y-%m-%d 12:00:00'),
            'stop': time.strftime('%Y-%m-%d 18:00:00'),
            'recurrency': True,
            'rrule': 'FREQ=MONTHLY;INTERVAL=1;COUNT=12;BYDAY=1MO'})

        # I check that the attributes are set correctly

        self.assertEqual(calendar_event_sprint_review.rrule_type, 'monthly', 'rrule_type should be mothly')
        self.assertEqual(calendar_event_sprint_review.count, 12, 'rrule_type should be mothly')
        self.assertEqual(calendar_event_sprint_review.month_by, 'day', 'rrule_type should be mothly')
        self.assertEqual(calendar_event_sprint_review.byday, '1', 'rrule_type should be mothly')
        self.assertEqual(calendar_event_sprint_review.week_list, 'MO', 'rrule_type should be mothly')
