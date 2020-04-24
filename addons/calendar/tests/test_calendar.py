# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from datetime import datetime, timedelta, time

from odoo import fields
from odoo.tests.common import TransactionCase
import pytz
import re


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
            (str(m.start_datetime), str(m.stop_datetime)),
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
            'start': datetime.combine(fields.Date.today(), time(12, 0)),
            'stop': datetime.combine(fields.Date.today(), time(18, 0)),
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
        self.assertEqual(
            (str(m.start_datetime), str(m.stop_datetime)),
            (u'2017-07-12 14:30:00', u'2017-07-12 15:00:00'),
            "Sanity check"
        )
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
            (str(m.start_datetime), str(m.stop_datetime)),
            ('2017-07-12 14:30:00', u'2017-07-12 15:00:00'),
        )
        self.assertEquals(
            (str(records.start_datetime), str(records.stop_datetime)),
            (u'2017-07-10 15:30:00', u'2017-07-10 16:00:00'),
        )

    def test_event_order(self):
        """ check the ordering of events when searching """
        def create_event(name, date):
            return self.CalendarEvent.create({
                'name': name,
                'start': date + ' 12:00:00',
                'stop': date + ' 14:00:00',
                'duration': 2.0,
            })
        foo1 = create_event('foo', '2011-04-01')
        foo2 = create_event('foo', '2011-06-01')
        bar1 = create_event('bar', '2011-05-01')
        bar2 = create_event('bar', '2011-06-01')
        domain = [('id', 'in', (foo1 + foo2 + bar1 + bar2).ids)]

        # sort them by name only
        events = self.CalendarEvent.search(domain, order='name')
        self.assertEqual(events.mapped('name'), ['bar', 'bar', 'foo', 'foo'])
        events = self.CalendarEvent.search(domain, order='name desc')
        self.assertEqual(events.mapped('name'), ['foo', 'foo', 'bar', 'bar'])

        # sort them by start date only
        events = self.CalendarEvent.search(domain, order='start')
        self.assertEqual(events.mapped('start'), (foo1 + bar1 + foo2 + bar2).mapped('start'))
        events = self.CalendarEvent.search(domain, order='start desc')
        self.assertEqual(events.mapped('start'), (foo2 + bar2 + bar1 + foo1).mapped('start'))

        # sort them by name then start date
        events = self.CalendarEvent.search(domain, order='name asc, start asc')
        self.assertEqual(list(events), [bar1, bar2, foo1, foo2])
        events = self.CalendarEvent.search(domain, order='name asc, start desc')
        self.assertEqual(list(events), [bar2, bar1, foo2, foo1])
        events = self.CalendarEvent.search(domain, order='name desc, start asc')
        self.assertEqual(list(events), [foo1, foo2, bar1, bar2])
        events = self.CalendarEvent.search(domain, order='name desc, start desc')
        self.assertEqual(list(events), [foo2, foo1, bar2, bar1])

        # sort them by start date then name
        events = self.CalendarEvent.search(domain, order='start asc, name asc')
        self.assertEqual(list(events), [foo1, bar1, bar2, foo2])
        events = self.CalendarEvent.search(domain, order='start asc, name desc')
        self.assertEqual(list(events), [foo1, bar1, foo2, bar2])
        events = self.CalendarEvent.search(domain, order='start desc, name asc')
        self.assertEqual(list(events), [bar2, foo2, bar1, foo1])
        events = self.CalendarEvent.search(domain, order='start desc, name desc')
        self.assertEqual(list(events), [foo2, bar2, bar1, foo1])

    def test_event_activity(self):
        # ensure meeting activity type exists
        meeting_act_type = self.env['mail.activity.type'].search([('category', '=', 'meeting')], limit=1)
        if not meeting_act_type:
            meeting_act_type = self.env['mail.activity.type'].create({
                'name': 'Meeting Test',
                'category': 'meeting',
            })

        # have a test model inheriting from activities
        test_record = self.env['res.partner'].create({
            'name': 'Test',
        })
        now = datetime.now()
        test_user = self.env.ref('base.user_demo')
        test_name, test_description, test_description2 = 'Test-Meeting', 'Test-Description', 'NotTest'
        test_note, test_note2 = '<p>Test-Description</p>', '<p>NotTest</p>'

        # create using default_* keys
        test_event = self.env['calendar.event'].sudo(test_user).with_context(
            default_res_model=test_record._name,
            default_res_id=test_record.id,
        ).create({
            'name': test_name,
            'description': test_description,
            'start': fields.Datetime.to_string(now + timedelta(days=-1)),
            'stop': fields.Datetime.to_string(now + timedelta(hours=2)),
            'user_id': self.env.user.id,
        })
        self.assertEqual(test_event.res_model, test_record._name)
        self.assertEqual(test_event.res_id, test_record.id)
        self.assertEqual(len(test_record.activity_ids), 1)
        self.assertEqual(test_record.activity_ids.summary, test_name)
        self.assertEqual(test_record.activity_ids.note, test_note)
        self.assertEqual(test_record.activity_ids.user_id, self.env.user)
        self.assertEqual(test_record.activity_ids.date_deadline, (now + timedelta(days=-1)).date())

        # updating event should update activity
        test_event.write({
            'name': '%s2' % test_name,
            'description': test_description2,
            'start': fields.Datetime.to_string(now + timedelta(days=-2)),
            'user_id': test_user.id,
        })
        self.assertEqual(test_record.activity_ids.summary, '%s2' % test_name)
        self.assertEqual(test_record.activity_ids.note, test_note2)
        self.assertEqual(test_record.activity_ids.user_id, test_user)
        self.assertEqual(test_record.activity_ids.date_deadline, (now + timedelta(days=-2)).date())

        # update event with a description that have a special character and a new line
        test_description3 = 'Test & \n Description'
        test_note3 = '<p>Test &amp; <br> Description</p>'
        test_event.write({
            'description': test_description3,
        })

        self.assertEqual(test_record.activity_ids.note, test_note3)

        # deleting meeting should delete its activity
        test_record.activity_ids.unlink()
        self.assertEqual(self.env['calendar.event'], self.env['calendar.event'].search([('name', '=', test_name)]))

        # create using active_model keys
        test_event = self.env['calendar.event'].sudo(self.env.ref('base.user_demo')).with_context(
            active_model=test_record._name,
            active_id=test_record.id,
        ).create({
            'name': test_name,
            'description': test_description,
            'start': now + timedelta(days=-1),
            'stop': now + timedelta(hours=2),
            'user_id': self.env.user.id,
        })
        self.assertEqual(test_event.res_model, test_record._name)
        self.assertEqual(test_event.res_id, test_record.id)
        self.assertEqual(len(test_record.activity_ids), 1)

    def test_event_allday(self):
        self.env.user.tz = 'Pacific/Honolulu'

        event = self.CalendarEvent.create({
            'name': 'All Day',
            'start': "2018-10-16 00:00:00",
            'start_date': "2018-10-16",
            'start_datetime': False,
            'stop': "2018-10-18 00:00:00",
            'stop_date': "2018-10-18",
            'stop_datetime': False,
            'allday': True,
        })

        self.assertEqual(str(event.start), '2018-10-16 08:00:00')
        self.assertEqual(str(event.stop), '2018-10-18 18:00:00')

    def test_recurring_around_dst(self):
        m = self.CalendarEvent.create({
            'name': "wheee",
            'start': '2018-10-27 14:30:00',
            'allday': False,
            'rrule': u'FREQ=DAILY;INTERVAL=1;COUNT=4',
            'duration': 2,
            'stop': '2018-10-27 16:30:00',
        })

        start_recurring_dates = m.with_context({'tz': 'Europe/Brussels'})._get_recurrent_date_by_event()
        self.assertEqual(len(start_recurring_dates), 4)

        for d in start_recurring_dates:
            self.assertEqual(d.tzinfo, pytz.UTC)
            if d.day < 28:  # DST switch happens between 2018-10-27 and 2018-10-28
                self.assertEqual(d.hour, 14)
            else:
                self.assertEqual(d.hour, 15)
            self.assertEqual(d.minute, 30)

    def test_event_activity_timezone(self):
        activty_type = self.env['mail.activity.type'].create({
            'name': 'Meeting',
            'category': 'meeting'
        })

        activity_id = self.env['mail.activity'].create({
            'summary': 'Meeting with partner',
            'activity_type_id': activty_type.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1).id,
            'res_id': self.env['res.partner'].search([('name', 'ilike', 'Deco Addict')], limit=1).id,
        })

        calendar_event = self.env['calendar.event'].create({
            'name': 'Meeting with partner',
            'activity_ids': [(6, False, activity_id.ids)],
            'start': '2018-11-12 21:00:00',
            'stop': '2018-11-13 00:00:00',
        })

        # Check output in UTC
        self.assertEqual(str(activity_id.date_deadline), '2018-11-12')

        # Check output in the user's tz
        # write on the event to trigger sync of activities
        calendar_event.with_context({'tz': 'Australia/Brisbane'}).write({
            'start': '2018-11-12 21:00:00',
        })

        self.assertEqual(str(activity_id.date_deadline), '2018-11-13')

    def test_event_allday_activity_timezone(self):
        # Covers use case of commit eef4c3b48bcb4feac028bf640b545006dd0c9b91
        # Also, read the comment in the code at calendar.event._inverse_dates
        activty_type = self.env['mail.activity.type'].create({
            'name': 'Meeting',
            'category': 'meeting'
        })

        activity_id = self.env['mail.activity'].create({
            'summary': 'Meeting with partner',
            'activity_type_id': activty_type.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1).id,
            'res_id': self.env['res.partner'].search([('name', 'ilike', 'Deco Addict')], limit=1).id,
        })

        calendar_event = self.env['calendar.event'].create({
            'name': 'All Day',
            'start': "2018-10-16 00:00:00",
            'start_date': "2018-10-16",
            'start_datetime': False,
            'stop': "2018-10-18 00:00:00",
            'stop_date': "2018-10-18",
            'stop_datetime': False,
            'allday': True,
            'activity_ids': [(6, False, activity_id.ids)],
        })

        # Check output in UTC
        self.assertEqual(str(activity_id.date_deadline), '2018-10-16')

        # Check output in the user's tz
        # write on the event to trigger sync of activities
        calendar_event.with_context({'tz': 'Pacific/Honolulu'}).write({
            'start': '2018-10-16 00:00:00',
            'start_date': '2018-10-16',
        })

        self.assertEqual(str(activity_id.date_deadline), '2018-10-16')

    def test_event_creation_mail(self):
        """
        Check that mail are sent to the attendees on event creation
        Check that mail are sent to the added attendees on event edit
        Check that mail are NOT sent to the attendees when detaching a recurring event
        """

        def _test_one_mail_per_attendee(self, m, partners):
            # check that every attendee receive a (single) mail for the event
            for partner in partners:
                mail = self.env['mail.mail'].search([
                    ('recipient_ids', 'in', partner.id),
                    ('subject', 'like', m.name),
                    ])
                self.assertEqual(len(mail), 1)

        partners = [
           self.env['res.partner'].create({'name':'testuser0','email': u'bob@example.com'}),
           self.env['res.partner'].create({'name':'testuser1','email': u'alice@example.com'}),
           ]
        partner_ids = [(6, False, [p.id for p in partners]),]
        now = fields.Datetime.now()
        m = self.CalendarEvent.create({
            'name': "mailTest1",
            'allday': False,
            'rrule': u'FREQ=DAILY;INTERVAL=1;COUNT=5',
            'duration': 0.5,
            'partner_ids': partner_ids,
            'start': fields.Datetime.to_string(now + timedelta(days=10)),
            'stop': fields.Datetime.to_string(now + timedelta(days=15)),
            })

        # every partner should have 1 mail sent
        _test_one_mail_per_attendee(self, m, partners)

        # adding more partners to the event
        partners.extend([
            self.env['res.partner'].create({'name':'testuser2','email': u'marc@example.com'}),
            self.env['res.partner'].create({'name':'testuser3','email': u'carl@example.com'}),
            self.env['res.partner'].create({'name':'testuser4','email': u'alain@example.com'}),
            ])
        partner_ids = [(6, False, [p.id for p in partners]),]
        m.write({'partner_ids': partner_ids})

        # more email should be sent
        _test_one_mail_per_attendee(self, m, partners)

        # calculate virtualid to detach one event
        virtid = str(m.id) + '-' + ''.join(re.split('[\D]', fields.Datetime.to_string(now + timedelta(days=12))))

        # detaching a virtual event in the chain
        self.env['calendar.event'].browse(virtid).detach_recurring_event(values={'active':False})

        # since the detach actually create an event in the backend
        # we check that no mail notifications are sent to the attendees
        _test_one_mail_per_attendee(self, m, partners)
