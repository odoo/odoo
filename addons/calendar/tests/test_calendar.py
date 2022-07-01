# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from datetime import datetime, timedelta, time

from odoo import fields, Command
from odoo.tests import Form
from odoo.addons.base.tests.common import SavepointCaseWithUserDemo
import pytz
import re


class TestCalendar(SavepointCaseWithUserDemo):

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

    def test_event_order(self):
        """ check the ordering of events when searching """
        def create_event(name, date):
            return self.CalendarEvent.create({
                'name': name,
                'start': date + ' 12:00:00',
                'stop': date + ' 14:00:00',
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
        test_user = self.user_demo
        test_name, test_description, test_description2 = 'Test-Meeting', 'Test-Description', 'NotTest'
        test_note, test_note2 = '<p>Test-Description</p>', '<p>NotTest</p>'

        # create using default_* keys
        test_event = self.env['calendar.event'].with_user(test_user).with_context(
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
        test_description3 = 'Test & <br> Description'
        test_note3 = '<p>Test &amp; <br> Description</p>'
        test_event.write({
            'description': test_description3,
        })

        self.assertEqual(test_record.activity_ids.note, test_note3)

        # deleting meeting should delete its activity
        test_record.activity_ids.unlink()
        self.assertEqual(self.env['calendar.event'], self.env['calendar.event'].search([('name', '=', test_name)]))

        # create using active_model keys
        test_event = self.env['calendar.event'].with_user(self.user_demo).with_context(
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
            'stop': "2018-10-18 00:00:00",
            'stop_date': "2018-10-18",
            'allday': True,
        })
        event.invalidate_cache()
        self.assertEqual(str(event.start), '2018-10-16 08:00:00')
        self.assertEqual(str(event.stop), '2018-10-18 18:00:00')

    def test_recurring_around_dst(self):
        m = self.CalendarEvent.create({
            'name': "wheee",
            'start': '2018-10-27 14:30:00',
            'allday': False,
            'rrule': u'FREQ=DAILY;INTERVAL=1;COUNT=4',
            'recurrency': True,
            'stop': '2018-10-27 16:30:00',
            'event_tz': 'Europe/Brussels',
        })

        start_recurring_dates = m.recurrence_id.calendar_event_ids.sorted('start').mapped('start')
        self.assertEqual(len(start_recurring_dates), 4)

        for d in start_recurring_dates:
            if d.day < 28:  # DST switch happens between 2018-10-27 and 2018-10-28
                self.assertEqual(d.hour, 14)
            else:
                self.assertEqual(d.hour, 15)
            self.assertEqual(d.minute, 30)

    def test_recurring_ny(self):
        self.env.user.tz = 'US/Eastern'
        f = Form(self.CalendarEvent.with_context(tz='US/Eastern'))
        f.name = 'test'
        f.start = '2022-07-07 01:00:00'  # This is in UTC. In NY, it corresponds to the 6th of july at 9pm.
        f.recurrency = True
        self.assertEqual(f.weekday, 'WED')

    def test_event_activity_timezone(self):
        activty_type = self.env['mail.activity.type'].create({
            'name': 'Meeting',
            'category': 'meeting'
        })

        activity_id = self.env['mail.activity'].create({
            'summary': 'Meeting with partner',
            'activity_type_id': activty_type.id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': self.env['res.partner'].create({'name': 'A Partner'}).id,
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
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': self.env['res.partner'].create({'name': 'A Partner'}).id,
        })

        calendar_event = self.env['calendar.event'].create({
            'name': 'All Day',
            'start': "2018-10-16 00:00:00",
            'start_date': "2018-10-16",
            'stop': "2018-10-18 00:00:00",
            'stop_date': "2018-10-18",
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
        Check that mail are NOT sent to the attendees when the event date is past
        """

        def _test_one_mail_per_attendee(self, partners):
            # check that every attendee receive a (single) mail for the event
            for partner in partners:
                mail = self.env['mail.message'].sudo().search([
                    ('notified_partner_ids', 'in', partner.id),
                    ])
                self.assertEqual(len(mail), 1)

        partners = [
            self.env['res.partner'].create({'name': 'testuser0', 'email': u'bob@example.com'}),
            self.env['res.partner'].create({'name': 'testuser1', 'email': u'alice@example.com'}),
        ]
        partner_ids = [(6, False, [p.id for p in partners]),]
        now = fields.Datetime.context_timestamp(partners[0], fields.Datetime.now())
        m = self.CalendarEvent.create({
            'name': "mailTest1",
            'allday': False,
            'rrule': u'FREQ=DAILY;INTERVAL=1;COUNT=5',
            'recurrency': True,
            'partner_ids': partner_ids,
            'start': fields.Datetime.to_string(now + timedelta(days=10)),
            'stop': fields.Datetime.to_string(now + timedelta(days=15)),
            })

        # every partner should have 1 mail sent
        _test_one_mail_per_attendee(self, partners)

        # adding more partners to the event
        partners.extend([
            self.env['res.partner'].create({'name': 'testuser2', 'email': u'marc@example.com'}),
            self.env['res.partner'].create({'name': 'testuser3', 'email': u'carl@example.com'}),
            self.env['res.partner'].create({'name': 'testuser4', 'email': u'alain@example.com'}),
            ])
        partner_ids = [(6, False, [p.id for p in partners]),]
        m.write({
            'partner_ids': partner_ids,
            'recurrence_update': 'all_events',
        })

        # more email should be sent
        _test_one_mail_per_attendee(self, partners)

        # create a new event in the past
        self.CalendarEvent.create({
            'name': "NOmailTest",
            'allday': False,
            'recurrency': False,
            'partner_ids': partner_ids,
            'start': fields.Datetime.to_string(now - timedelta(days=10)),
            'stop': fields.Datetime.to_string(now - timedelta(days=9)),
        })

        # no more email should be sent
        _test_one_mail_per_attendee(self, partners)

    def test_event_creation_sudo_other_company(self):
        """ Check Access right issue when create event with sudo

            Create a company, a user in that company
            Create an event for someone else in another company as sudo
            Should not failed for acces right check
        """
        now = fields.Datetime.context_timestamp(self.partner_demo, fields.Datetime.now())

        web_company = self.env['res.company'].sudo().create({'name': "Website Company"})
        web_user = self.env['res.users'].with_company(web_company).sudo().create({
            'name': 'web user',
            'login': 'web',
            'company_id': web_company.id
        })
        self.CalendarEvent.with_user(web_user).with_company(web_company).sudo().create({
            'name': "Test",
            'allday': False,
            'recurrency': False,
            'partner_ids': [(6, 0, self.partner_demo.ids)],
            'alarm_ids': [(0, 0, {
                'name': 'Alarm',
                'alarm_type': 'notification',
                'interval': 'minutes',
                'duration': 30,
            })],
            'user_id': self.user_demo.id,
            'start': fields.Datetime.to_string(now + timedelta(hours=5)),
            'stop': fields.Datetime.to_string(now + timedelta(hours=6)),
        })

    def test_meeting_creation_from_partner_form(self):
        """ When going from a partner to the Calendar and adding a meeting, both current user and partner
         should be attendees of the event """
        calendar_action = self.partner_demo.schedule_meeting()
        event = self.env['calendar.event'].with_context(calendar_action['context']).create({
            'name': 'Super Meeting',
            'start': datetime(2020, 12, 13, 17),
            'stop': datetime(2020, 12, 13, 22),
        })
        self.assertEqual(len(event.attendee_ids), 2)
        self.assertTrue(self.partner_demo in event.attendee_ids.mapped('partner_id'))
        self.assertTrue(self.env.user.partner_id in event.attendee_ids.mapped('partner_id'))

    def test_discuss_videocall(self):
        self.event_tech_presentation._set_discuss_videocall_location()
        self.assertFalse(self.event_tech_presentation.videocall_channel_id.id, 'No channel should be set before the route is accessed')
        # create the first channel
        self.event_tech_presentation._create_videocall_channel()
        self.assertNotEqual(self.event_tech_presentation.videocall_channel_id.id, False)

        partner1 = self.env['res.partner'].create({'name': 'Bob', 'email': u'bob@gm.co'})
        partner2 = self.env['res.partner'].create({'name': 'Jack', 'email': u'jack@gm.co'})
        new_partners = [partner1.id, partner2.id]
        # invite partners to meeting
        self.event_tech_presentation.write({
            'partner_ids': [Command.link(new_partner) for new_partner in new_partners]
        })
        self.assertTrue(set(new_partners) == set(self.event_tech_presentation.videocall_channel_id.channel_partner_ids.ids), 'new partners must be invited to the channel')
