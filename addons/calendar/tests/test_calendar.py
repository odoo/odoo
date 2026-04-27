# Part of Odoo. See LICENSE file for full copyright and licensing details.

import freezegun

from datetime import datetime, timedelta

from odoo import fields, Command
from odoo.exceptions import AccessError
from odoo.tests import tagged, Form, new_test_user
from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


@tagged('at_install', '-post_install')  # LEGACY at_install
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
        f.end_type = 'count'
        self.assertEqual(f.weekday, 'WED')
        self.assertEqual(f.event_tz, 'America/New_York', "The value should correspond to the user tz")
        self.assertEqual(f.count, 1, "The default value should be displayed")
        self.assertEqual(f.interval, 1, "The default value should be displayed")
        self.assertEqual(f.month_by, "date", "The default value should be displayed")
        self.assertEqual(f.end_type, "count", "The default value should be displayed")
        self.assertEqual(f.rrule_type, "weekly", "The default value should be displayed")

    @freezegun.freeze_time('2011-04-29 10:00:00')
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

    def test_search_current_attendee_status(self):
        """ Test searching for events based on the current user's attendance status. """
        # Create a second user to ensure the filter is specific to the current user
        user_test = new_test_user(self.env, login='user_test_calendar_filter')

        # Create events with different attendee statuses for both users
        event_accepted = self.env['calendar.event'].create({
            'name': 'Event Demo Accepted',
            'start': datetime(2025, 1, 1, 10, 0),
            'stop': datetime(2025, 1, 1, 11, 0),
            'attendee_ids': [
                Command.create({'partner_id': self.user_demo.partner_id.id, 'state': 'accepted'}),
                Command.create({'partner_id': user_test.partner_id.id, 'state': 'needsAction'}),
            ]
        })
        event_declined = self.env['calendar.event'].create({
            'name': 'Event Demo Declined',
            'start': datetime(2025, 1, 2, 10, 0),
            'stop': datetime(2025, 1, 2, 11, 0),
            'attendee_ids': [
                Command.create({'partner_id': self.user_demo.partner_id.id, 'state': 'declined'}),
                Command.create({'partner_id': user_test.partner_id.id, 'state': 'accepted'}),
            ]
        })
        event_tentative = self.env['calendar.event'].create({
            'name': 'Event Demo Tentative',
            'start': datetime(2025, 1, 3, 10, 0),
            'stop': datetime(2025, 1, 3, 11, 0),
            'attendee_ids': [
                Command.create({'partner_id': self.user_demo.partner_id.id, 'state': 'tentative'}),
                Command.create({'partner_id': user_test.partner_id.id, 'state': 'declined'}),
            ]
        })
        event_other_user = self.env['calendar.event'].create({
            'name': 'Event Other User Only',
            'start': datetime(2025, 1, 4, 10, 0),
            'stop': datetime(2025, 1, 4, 11, 0),
            'attendee_ids': [
                Command.create({'partner_id': user_test.partner_id.id, 'state': 'accepted'}),
            ]
        })

        # Perform searches as the demo user and assert the results
        CalendarEvent_Demo = self.env['calendar.event'].with_user(self.user_demo)

        # Search for 'Yes' (accepted)
        accepted_events = CalendarEvent_Demo.search([('current_status', '=', 'accepted')])
        self.assertEqual(accepted_events, event_accepted, "Should find only the event where the demo user has accepted.")

        # Search for 'No' (declined)
        declined_events = CalendarEvent_Demo.search([('current_status', '=', 'declined')])
        self.assertEqual(declined_events, event_declined, "Should find only the event where the demo user has declined.")

        # Search for 'Maybe' (tentative)
        tentative_events = CalendarEvent_Demo.search([('current_status', '=', 'tentative')])
        self.assertEqual(tentative_events, event_tentative, "Should find only the event where the demo user is tentative.")

        # Search for events where status is not 'No' (declined)
        not_declined_events = CalendarEvent_Demo.search([('current_status', '!=', 'declined')])
        self.assertIn(event_accepted, not_declined_events, "Accepted events should be in the result.")
        self.assertIn(event_tentative, not_declined_events, "Tentative events should be in the result.")
        self.assertNotIn(event_declined, not_declined_events, "Declined events should NOT be in the result.")
        self.assertNotIn(event_other_user, not_declined_events, "Events where the user is not an attendee should NOT be in the result.")

        # Search using the 'in' operator
        in_events = CalendarEvent_Demo.search([('current_status', 'in', ['accepted', 'tentative'])])
        self.assertEqual(len(in_events), 2, "Should find two events for 'accepted' or 'tentative'.")
        self.assertIn(event_accepted, in_events, "Should find the accepted event in the 'in' search.")
        self.assertIn(event_tentative, in_events, "Should find the tentative event in the 'in' search.")


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

    def test_event_privacy_domain(self):
        """Test privacy domain filtering in _read_group for events with user_id=False and default privacy (False)"""
        now = datetime.now()
        test_user = self.user_demo

        self.env['calendar.event'].create([
            {
                'name': 'event_a',
                'start': now + timedelta(days=-1),
                'stop': now + timedelta(days=-1, hours=2),
                'user_id': False,
                'privacy': 'public',
            },
            {
                'name': 'event_b',
                'start': now + timedelta(days=1),
                'stop': now + timedelta(days=1, hours=1),
                'user_id': False,
                'privacy': False,
            },
            {
                'name': 'event_c',
                'start': now + timedelta(days=-1, hours=3),
                'stop': now + timedelta(days=-1, hours=5),
                'user_id': False,
                'privacy': 'private',
            }
        ])

        meetings = self.env['calendar.event'].with_user(test_user)
        result = meetings._read_group(
            domain=[['user_id', '=', False]],
            aggregates=["__count", "duration:sum"],
            groupby=['create_date:month']
        )

        # Verify privacy domain filtered out the private event only
        total_visible_events = sum(group[1] for group in result)
        self.assertEqual(total_visible_events, 2,
                        "Should see 2 events (public and no-privacy), private event filtered out")

    def test_unauthorized_user_cannot_add_attendee(self):
        """ Check that a user that doesn't have access to a private event cannot add attendees to it """
        attendee_model = self.env['calendar.attendee'].with_user(self.user_demo.id)
        # event_id in values
        with self.assertRaises(AccessError):
            attendee_model.create([{
                'event_id': self.event_tech_presentation.id,
                'partner_id': self.partner_demo.id,
            }])
        # event_id via context (default_event_id)
        with self.assertRaises(AccessError):
            attendee_model.with_context(default_event_id=self.event_tech_presentation.id).create([{
                'partner_id': self.partner_demo.id,
            }])

    def test_default_duration(self):
        # Check the default duration depending on various parameters
        user_demo = self.user_demo
        second_company = self.env['res.company'].sudo().create({'name': "Second Company"})

        duration = self.env['calendar.event'].get_default_duration()
        self.assertEqual(duration, 1, "By default, the duration is 1 hour")

        IrDefault = self.env['ir.default'].sudo()
        IrDefault.with_user(user_demo).set('calendar.event', 'duration', 2, user_id=True, company_id=False)
        IrDefault.with_company(second_company).set('calendar.event', 'duration', 8, company_id=True)

        duration = self.env['calendar.event'].with_user(user_demo).get_default_duration()
        self.assertEqual(duration, 2, "Custom duration is 2 hours")

        duration = self.env['calendar.event'].with_company(second_company).get_default_duration()
        self.assertEqual(duration, 8, "Custom duration is 8 hours in the other company")

    def test_discuss_videocall_not_ringing_with_event(self):
        self.event_tech_presentation._set_discuss_videocall_location()
        self.event_tech_presentation._create_videocall_channel()
        self.event_tech_presentation.write(
            {
                "start": fields.Datetime.to_string(datetime.now() + timedelta(hours=2)),
            }
        )

        partner1, partner2 = self.env["res.partner"].create(
            [{"name": "Bob", "email": "bob@gm.co"}, {"name": "Jack", "email": "jack@gm.co"}]
        )
        new_partners = [partner1.id, partner2.id]
        # invite partners to meeting
        self.event_tech_presentation.write(
            {"partner_ids": [Command.link(new_partner) for new_partner in new_partners]}
        )

        channel_member = self.event_tech_presentation.videocall_channel_id.channel_member_ids[0]
        channel_member_2 = self.event_tech_presentation.videocall_channel_id.channel_member_ids[1]
        channel_member._rtc_join_call()
        self.assertFalse(channel_member_2.rtc_inviting_session_id)

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

    def test_contact_details_single_vs_multiple_attendees(self):
        """Contact Details section should only appear for 1-on-1 meetings
        (single non-organizer attendee)."""
        organizer = new_test_user(self.env, login='org_user', groups='base.group_user')
        attendees = self.env['res.partner'].create([
            {'name': 'Attendee A', 'email': 'a@test.com', 'phone': '+1000000001'},
            {'name': 'Attendee B', 'email': 'b@test.com', 'phone': '+1000000002'},
            {'name': 'Attendee C', 'email': 'c@test.com', 'phone': '+1000000003'},
        ])
        # Multiple attendees: only organizer info is shown
        event_multi = self.env['calendar.event'].with_user(organizer).create({
            'name': 'Group Meeting',
            'start': '2026-04-01 10:00:00',
            'stop': '2026-04-01 11:00:00',
            'user_id': organizer.id,
            'partner_ids': [Command.link(pid) for pid in attendees.ids],
        })
        self.assertIn('Organized by', event_multi.description)
        self.assertNotIn('Contact Details', event_multi.description)
        for attendee in attendees:
            self.assertNotIn(attendee.name, event_multi.description)
        # Single attendee: Contact Details should appear
        event_single = self.env['calendar.event'].with_user(organizer).create({
            'name': '1-on-1 Meeting',
            'start': '2026-04-01 12:00:00',
            'stop': '2026-04-01 13:00:00',
            'user_id': organizer.id,
            'partner_ids': [Command.link(attendees[0].id)],
        })
        self.assertIn('Organized by', event_single.description)
        self.assertIn('Contact Details', event_single.description)
        self.assertIn('Attendee A', event_single.description)
