# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from datetime import date, datetime, timedelta

from odoo import fields, Command
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests import Form, tagged, new_test_user
from odoo.addons.base.tests.common import SavepointCaseWithUserDemo

import freezegun
import pytz
import re
import base64


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

    def test_event_activity_user_sync(self):
        # ensure phonecall activity type exists
        activty_type = self.env['mail.activity.type'].create({
            'name': 'Call',
            'category': 'phonecall'
        })
        activity = self.env['mail.activity'].create({
            'summary': 'Call with Demo',
            'activity_type_id': activty_type.id,
            'note': 'Schedule call with Admin',
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'user_id': self.user_demo.id,
        })
        action_context = activity.action_create_calendar_event().get('context', {})
        event_from_activity = self.env['calendar.event'].with_context(action_context).create({
            'start': '2022-07-27 14:30:00',
            'stop': '2022-07-27 16:30:00',
        })
        # Check that assignation of the activity hasn't changed, and event is having
        # correct values set in attendee and organizer related fields
        self.assertEqual(activity.user_id, self.user_demo)
        self.assertEqual(event_from_activity.partner_ids, activity.user_id.partner_id)
        self.assertEqual(event_from_activity.attendee_ids.partner_id, activity.user_id.partner_id)
        self.assertEqual(event_from_activity.user_id, activity.user_id)

    def test_activity_event_multiple_meetings(self):
        # Creating multiple meetings from an activity creates additional activities
        # ensure meeting activity type exists
        meeting_act_type = self.env.ref('mail.mail_activity_data_meeting')

        # have a test model inheriting from activities
        test_record = self.env['res.partner'].create({
            'name': 'Test',
        })

        activity_1 = self.env['mail.activity'].create({
            'summary': 'Meeting 1 with partner',
            'activity_type_id': meeting_act_type.id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': test_record.id,
        })

        # default usage in successive create
        event_1_1 = self.env['calendar.event'].with_context(default_activity_ids=[(6, 0, activity_1.ids)]).create({
            'name': 'Meeting 1',
            'start': datetime(2025, 3, 10, 17),
            'stop': datetime(2025, 3, 10, 22),
        })
        self.assertEqual(event_1_1.activity_ids, activity_1)
        self.assertEqual(activity_1.calendar_event_id, event_1_1)
        self.assertEqual(activity_1.date_deadline, date(2025, 3, 10))
        event_1_2 = self.env['calendar.event'].with_context(default_activity_ids=[(6, 0, activity_1.ids)]).create({
            'name': 'Meeting 2',
            'start': datetime(2025, 3, 12, 17),
            'stop': datetime(2025, 3, 12, 22),
        })
        self.assertFalse(event_1_1.activity_ids, 'Changes activity ownership')
        self.assertEqual(event_1_2.activity_ids, activity_1, 'Changes activity ownership')
        self.assertEqual(activity_1.calendar_event_id, event_1_2)
        self.assertEqual(activity_1.date_deadline, date(2025, 3, 12))

        activity_2 = self.env['mail.activity'].create({
            'summary': 'Meeting 2 with partner',
            'activity_type_id': meeting_act_type.id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': test_record.id,
        })
        existing_activities = self.env['mail.activity'].search([])

        # specific action that creates activities instead of replacing
        calendar_action = activity_2.with_context(default_res_model='res.partner', default_res_id=test_record.id).action_create_calendar_event()
        event_2_1 = self.env['calendar.event'].with_context(calendar_action['context']).create({
            'name': 'Meeting 1',
            'start': datetime(2025, 4, 10, 17),
            'stop': datetime(2025, 4, 10, 22),
        })
        self.assertEqual(event_2_1.activity_ids, activity_2)
        self.assertEqual(activity_2.calendar_event_id, event_2_1)
        self.assertEqual(activity_2.date_deadline, date(2025, 4, 10))

        event_2_2 = self.env['calendar.event'].with_context(calendar_action['context']).create({
            'name': 'Meeting 2',
            'start': datetime(2025, 4, 11, 17),
            'stop': datetime(2025, 4, 11, 22),
        })
        new_existing_activities = self.env['mail.activity'].search([])
        new_activity = new_existing_activities - existing_activities
        self.assertEqual(event_2_1.activity_ids, activity_2, "Event 1's activity should still be the first activity")
        self.assertEqual(activity_2.calendar_event_id, event_2_1, "The first activity's event should still be event 1")

        self.assertEqual(len(new_activity), 1, "1 more activity record should have been created (by event 2)")
        self.assertEqual(event_2_2.activity_ids, new_activity, "Event 2's activity should not be the first activity")
        self.assertEqual(event_2_2.activity_ids.activity_type_id, activity_2.activity_type_id, "Event 2's activity should be the same activity type as the first activity")
        self.assertEqual(test_record.activity_ids, activity_1 + activity_2 + new_activity, "Resource record should now have all activities")

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
        self.env.invalidate_all()
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
        self.user_demo.tz = 'America/New_York'
        event = self.CalendarEvent.create({'user_id': self.user_demo.id, 'name': 'test', 'partner_ids': [Command.link(self.user_demo.partner_id.id)]})
        f = Form(event.with_context(tz='America/New_York').with_user(self.user_demo))
        f.name = 'test'
        f.start = '2022-07-07 01:00:00'  # This is in UTC. In NY, it corresponds to the 6th of july at 9pm.
        f.recurrency = True
        self.assertEqual(f.weekday, 'WED')
        self.assertEqual(f.event_tz, 'America/New_York', "The value should correspond to the user tz")
        self.assertEqual(f.count, 1, "The default value should be displayed")
        self.assertEqual(f.interval, 1, "The default value should be displayed")
        self.assertEqual(f.month_by, "date", "The default value should be displayed")
        self.assertEqual(f.end_type, "count", "The default value should be displayed")
        self.assertEqual(f.rrule_type, "weekly", "The default value should be displayed")

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

    @freezegun.freeze_time('2023-10-06 10:00:00')
    def test_event_creation_mail(self):
        """
        Freezegun used because we don't send mail for past events
        Check that mail are sent to the attendees on event creation
        Check that mail are sent to the added attendees on event edit
        Check that mail are NOT sent to the attendees when the event date is past
        Check that mail have extra attachement added by the user
        """

        def _test_one_mail_per_attendee(self, partners):
            # check that every attendee receive a (single) mail for the event
            for partner in partners:
                mail = self.env['mail.message'].sudo().search([
                    ('notified_partner_ids', 'in', partner.id),
                    ])
                self.assertEqual(len(mail), 1)

        def _test_emails_has_attachment(self, partners, attachments_names=["fileText_attachment.txt"], checksums=None):
            # check that every email has specified extra attachments
            for partner in partners:
                mail = self.env['mail.message'].sudo().search([
                    ('notified_partner_ids', 'in', partner.id),
                ])
                extra_attachments = mail.attachment_ids.filtered(lambda attachment: attachment.name in attachments_names)
                self.assertEqual(len(extra_attachments), len(attachments_names))
                if checksums:
                    self.assertEqual(extra_attachments.mapped('checksum'), checksums)

        attachments = self.env['ir.attachment'].create([{
            'datas': base64.b64encode(bytes("Event Attachment", 'utf-8')),
            'name': 'fileText_attachment.txt',
            'mimetype': 'text/plain'
        }, {
            'datas': base64.b64encode(bytes("Event Attachment 2", 'utf-8')),
            'name': 'fileText_attachment_2.txt',
            'mimetype': 'text/plain'
        }])
        self.env.ref('calendar.calendar_template_meeting_invitation').attachment_ids = attachments

        partners = [
            self.env['res.partner'].create({'name': 'testuser0', 'email': u'bob@example.com'}),
            self.env['res.partner'].create({'name': 'testuser1', 'email': u'alice@example.com'}),
        ]
        partner_ids = [(6, False, [p.id for p in partners]),]
        m = self.CalendarEvent.create({
            'name': "mailTest1",
            'allday': False,
            'rrule': u'FREQ=DAILY;INTERVAL=1;COUNT=5',
            'recurrency': True,
            'partner_ids': partner_ids,
            'start': "2023-10-29 08:00:00",
            'stop': "2023-11-03 08:00:00",
            })

        # every partner should have 1 mail sent
        _test_one_mail_per_attendee(self, partners)
        _test_emails_has_attachment(self, partners, checksums=[attachments[0].checksum])

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
            'start': "2023-10-04 08:00:00",
            'stop': "2023-10-10 08:00:00",
        })

        # no more email should be sent
        _test_one_mail_per_attendee(self, partners)

        partner_staff, new_partner = self.env['res.partner'].create([{
            'name': 'partner_staff',
            'email': 'partner_staff@example.com',
        }, {
            'name': 'partner_created_on_the_spot_by_the_appointment_form',
            'email': 'partner_created_on_the_spot_by_the_appointment_form@example.com',
        }])
        self.CalendarEvent.with_user(self.env.ref('base.public_user')).sudo().create({
            'name': "publicUserEvent",
            'partner_ids': [(6, False, [partner_staff.id, new_partner.id])],
            'start': "2023-10-06 12:00:00",
            'stop': "2023-10-06 13:00:00",
        })
        _test_emails_has_attachment(
            self, partners=[partner_staff, new_partner], attachments_names=[a.name for a in attachments], checksums=attachments.mapped('checksum')
        )

    def test_event_creation_internal_user_invitation_ics(self):
        """ Check that internal user can read invitation.ics attachment """
        internal_user = new_test_user(self.env, login='internal_user', groups='base.group_user')

        partner = internal_user.partner_id
        self.event_tech_presentation.write({
            'partner_ids': [(4, partner.id)],
        })
        msg = self.env['mail.message'].search([
            ('notified_partner_ids', 'in', partner.id),
        ])
        msg.invalidate_recordset()


        # internal user can read the attachment without errors
        self.assertEqual(msg.with_user(internal_user).attachment_ids.name, 'invitation.ics')

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

    def test_event_duplication_allday(self):
        """Test that a calendar event is successfully duplicated with dates."""
        # Create an event
        calendar_event = self.env['calendar.event'].create({
            'name': 'All Day',
            'start': "2018-10-16 00:00:00",
            'start_date': "2018-10-16",
            'stop': "2018-10-18 00:00:00",
            'stop_date': "2018-10-18",
            'allday': True,
        })
        # Duplicate the event with explicit defaults for start_date and stop_date
        new_calendar_event = calendar_event.copy()
        # Ensure the copied event exists and retains the correct dates
        self.assertTrue(new_calendar_event, "Event should be duplicated.")
        self.assertEqual(new_calendar_event.start_date, calendar_event.start_date, "Start date should match the original.")
        self.assertEqual(new_calendar_event.stop_date, calendar_event.stop_date, "Stop date should match the original.")

@tagged('post_install', '-at_install')
class TestCalendarTours(HttpCaseWithUserDemo):
    def test_calendar_month_view_start_hour_displayed(self):
        """ Test that the time is displayed in the month view. """
        self.start_tour("/web", 'calendar_appointments_hour_tour', login="demo")

    def test_calendar_delete_tour(self):
        """
            Check that we can delete events with the "Everybody's calendars" filter.
        """
        user_admin = self.env.ref('base.user_admin')
        start = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
        stop = datetime.combine(date.today(), datetime.min.time()).replace(hour=12)
        event = self.env['calendar.event'].with_user(user_admin).create({
            'name': 'Test Event',
            'description': 'Test Description',
            'start': start.strftime("%Y-%m-%d %H:%M:%S"),
            'stop': stop.strftime("%Y-%m-%d %H:%M:%S"),
            'duration': 3,
            'location': 'Odoo S.A.',
            'privacy': 'public',
            'show_as': 'busy',
        })
        action_id = self.env.ref('calendar.action_calendar_event')
        url = "/web#action=" + str(action_id.id) + '&view_type=calendar'
        self.start_tour(url, 'test_calendar_delete_tour', login='admin')
        event = self.env['calendar.event'].search([('name', '=', 'Test Event')])
        self.assertFalse(event) # Check if the event has been correctly deleted

    def test_calendar_decline_tour(self):
        """
            Check that we can decline events.
        """
        user_admin = self.env.ref('base.user_admin')
        user_demo = self.user_demo
        start = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
        stop = datetime.combine(date.today(), datetime.min.time()).replace(hour=12)
        event = self.env['calendar.event'].with_user(user_admin).create({
            'name': 'Test Event',
            'description': 'Test Description',
            'start': start.strftime("%Y-%m-%d %H:%M:%S"),
            'stop': stop.strftime("%Y-%m-%d %H:%M:%S"),
            'duration': 3,
            'location': 'Odoo S.A.',
            'privacy': 'public',
            'show_as': 'busy',
        })
        event.partner_ids = [Command.link(user_demo.partner_id.id)]
        action_id = self.env.ref('calendar.action_calendar_event')
        url = "/web#action=" + str(action_id.id) + '&view_type=calendar'
        self.start_tour(url, 'test_calendar_decline_tour', login='demo')
        attendee = self.env['calendar.attendee'].search([('event_id', '=', event.id), ('partner_id', '=', user_demo.partner_id.id)])
        self.assertEqual(attendee.state, 'declined') # Check if the event has been correctly declined

    def test_calendar_decline_with_everybody_filter_tour(self):
        """
            Check that we can decline events with the "Everybody's calendars" filter.
        """
        user_admin = self.env.ref('base.user_admin')
        user_demo = self.user_demo
        start = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
        stop = datetime.combine(date.today(), datetime.min.time()).replace(hour=12)
        event = self.env['calendar.event'].with_user(user_admin).create({
            'name': 'Test Event',
            'description': 'Test Description',
            'start': start.strftime("%Y-%m-%d %H:%M:%S"),
            'stop': stop.strftime("%Y-%m-%d %H:%M:%S"),
            'duration': 3,
            'location': 'Odoo S.A.',
            'privacy': 'public',
            'show_as': 'busy',
        })
        event.partner_ids = [Command.link(user_demo.partner_id.id)]
        action_id = self.env.ref('calendar.action_calendar_event')
        url = "/web#action=" + str(action_id.id) + '&view_type=calendar'
        self.start_tour(url, 'test_calendar_decline_with_everybody_filter_tour', login='demo')
        attendee = self.env['calendar.attendee'].search([('event_id', '=', event.id), ('partner_id', '=', user_demo.partner_id.id)])
        self.assertEqual(attendee.state, 'declined') # Check if the event has been correctly declined

    def test_calendar_res_id_fallback_when_res_id_is_0(self):
        user_admin = self.env.ref('base.user_admin')
        context_defaults = {
            'default_res_model': user_admin._name,
            'default_res_id': user_admin.id,
        }

        self.env['mail.activity.type'].create({
            'name': 'Meeting',
            'category': 'meeting'
        })

        event = self.env['calendar.event'].with_user(user_admin).with_context(**context_defaults).create({
            'name': 'All Day',
            'start': "2018-10-16 00:00:00",
            'start_date': "2018-10-16",
            'stop': "2018-10-18 00:00:00",
            'stop_date': "2018-10-18",
            'allday': True,
            'res_id': 0,
        })
        self.assertTrue(event.res_id)
