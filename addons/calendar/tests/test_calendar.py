# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import fields
from odoo.tests.common import TransactionCase


class TestCalendar(TransactionCase):

    def setUp(self):
        super(TestCalendar, self).setUp()

        self.CalendarEvent = self.env['calendar.event']
        # In Order to test calendar, I will first create One Simple Event with real data
        self.event_tech_presentation = self.CalendarEvent.create({
            'privacy': 'private',
            'start': '2011-04-30 16:00:00',
            'stop': '2011-04-30 18:30:00',
            'description': 'The Technical Presentation will cover following topics:\n* Creating Odoo class\n* Views\n* Wizards\n* Workflows',
            'duration': 2.5,
            'location': 'Odoo S.A.',
            'name': 'Technical Presentation'
        })

    def test_calender_simple_event(self):
        m = self.CalendarEvent.create({
            'name': "Test compute",
            'start': '2017-07-12 14:30:00',
            'allday': False,
            'stop': '2017-07-12 15:00:00',
        })

        self.assertEqual(
            (m.start_datetime, m.stop_datetime),
            (u'2017-07-12 14:30:00', u'2017-07-12 15:00:00'),
            "Sanity check"
        )

    def test_calender_event(self):
        # Now I will set recurrence for this event to occur monday and friday of week
        data = {
            'fr': 1,
            'mo': 1,
            'interval': 1,
            'rrule_type': 'weekly',
            'end_type': 'end_date',
            'final_date': '2011-05-31 00:00:00',
            'recurrency': True
        }

        self.event_tech_presentation.write(data)

        # In order to check that recurrent events are views successfully in calendar view, I will open calendar view of events|
        self.CalendarEvent.fields_view_get(False, 'calendar')

        # In order to check that recurrent events are views successfully in calendar view, I will search for one of the recurrent event and count the number of events
        rec_events = self.CalendarEvent.with_context({'virtual_id': True}).search([
            ('start', '>=', '2011-04-30 16:00:00'), ('start', '<=', '2011-05-31 00:00:00')
        ])
        self.assertEqual(len(rec_events), 9, 'Wrong number of events found')

        # Now I move a virtual event, to see that a real event is well created and depending from the native recurrence
        before = self.CalendarEvent.with_context({'virtual_id': False}).search([
            ('start', '>=', '2011-04-30 16:00:00'), ('start', '<=', '2011-05-31 00:00:00')
        ])

        # We start by detach the event
        newevent = rec_events[1].detach_recurring_event()
        newevent.with_context({'virtual_id': True}).write({'name': 'New Name', 'recurrency': True})
        after = self.CalendarEvent.with_context({'virtual_id': False}).search([
            ('start', '>=', '2011-04-30 16:00:00'), ('start', '<=', '2011-05-31 00:00:00')
        ])
        self.assertEqual(len(after), len(before) + 1, 'Wrong number of events found, after to have moved a virtual event')
        new_event = after - before
        self.assertEqual(new_event[0].recurrent_id, before.id, 'Recurrent_id not correctly passed to the new event')

        # Now I will test All day event
        allday_event = self.CalendarEvent.create({
            'allday': 1,
            'privacy': 'confidential',
            'start': '2011-04-30 00:00:00',
            'stop': '2011-04-30 00:00:00',
            'description': 'All day technical test',
            'location': 'School',
            'name': 'All day test event'
        })

        # In order to check reminder I will first create reminder
        res_alarm_day_before_event_starts = self.env['calendar.alarm'].create({
            'name': '1 Day before event starts',
            'duration': 1,
            'interval': 'days',
            'type': 'notification'
        })

        # Now I will assign this reminder to all day event|
        allday_event.write({'alarm_ids': [(6, 0, [res_alarm_day_before_event_starts.id])]})

        # I create a recuring rule for my event
        calendar_event_sprint_review = self.CalendarEvent.create({
            'name': 'Begin of month meeting',
            'start': fields.Date.today() + ' 12:00:00',
            'stop': fields.Date.today() + ' 18:00:00',
            'recurrency': True,
            'rrule': 'FREQ=MONTHLY;INTERVAL=1;COUNT=12;BYDAY=1MO'
        })

        # I check that the attributes are set correctly
        self.assertEqual(calendar_event_sprint_review.rrule_type, 'monthly', 'rrule_type should be mothly')
        self.assertEqual(calendar_event_sprint_review.count, 12, 'rrule_type should be mothly')
        self.assertEqual(calendar_event_sprint_review.month_by, 'day', 'rrule_type should be mothly')
        self.assertEqual(calendar_event_sprint_review.byday, '1', 'rrule_type should be mothly')
        self.assertEqual(calendar_event_sprint_review.week_list, 'MO', 'rrule_type should be mothly')

    def test_validation_error(self):
        """
        Ideally this should build the base event in such a way that calling
        write() triggers detach_recurring_event, but I've no idea how that
        actually works so just calling it directly for now
        """
        m = self.CalendarEvent.create({
            'name': "wheee",
            'start': '2017-07-12 14:30:00',
            'allday': False,
            'rrule': u'FREQ=WEEKLY;BYDAY=WE;INTERVAL=1;COUNT=100',
            'duration': 0.5,
            'stop': '2017-07-12 15:00:00',
        })

        values = {
            'allday': False,
            'name': u'wheee',
            'attendee_ids': [
                (0, 0, {'state': u'needsAction', 'partner_id': 8, 'email': u'bob@example.com'}),
                (0, 0, {'state': u'needsAction', 'partner_id': 10, 'email': u'ed@example.com'}),
            ],
            'recurrency': True,
            'privacy': u'public',
            'stop': '2017-07-10 16:00:00',
            'alarm_ids': [(6, 0, [])],
            'start': '2017-07-10 15:30:00',
            'location': u"XXX",
            'duration': 0.5,
            'partner_ids': [(4, 10), (4, 8)],
            'description': u"A thing"
        }

        records = m.detach_recurring_event(values)
        self.assertEqual(
            (m.start_datetime, m.stop_datetime),
            (u'2017-07-12 14:30:00', u'2017-07-12 15:00:00'),
        )
        self.assertEquals(
            (records.start_datetime, records.stop_datetime),
            (u'2017-07-10 15:30:00', u'2017-07-10 16:00:00'),
        )
