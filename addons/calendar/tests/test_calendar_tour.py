# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo import Command
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mail.tests.common import MailCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestCalendarTours(HttpCaseWithUserDemo, MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.user_admin').write({
            'email': 'mitchell.admin@example.com',
        })

    def test_calendar_month_view_start_hour_displayed(self):
        """ Test that the time is displayed in the month view. """
        self.start_tour("/odoo", 'calendar_appointments_hour_tour', login="demo")

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
        url = "/odoo/action-" + str(action_id.id)
        self.start_tour(url, 'test_calendar_delete_tour', login='admin')
        event = self.env['calendar.event'].search([('name', '=', 'Test Event')])
        self.assertFalse(event)  # Check if the event has been correctly deleted

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
        url = "/odoo/action-" + str(action_id.id)
        self.start_tour(url, 'test_calendar_decline_tour', login='demo')
        attendee = self.env['calendar.attendee'].search([('event_id', '=', event.id), ('partner_id', '=', user_demo.partner_id.id)])
        self.assertEqual(attendee.state, 'declined')  # Check if the event has been correctly declined

    def test_calendar_invite_tour(self):
        """Check that the modal allowing to send invitations is displayed when new attendees are added and that they receive them."""
        created_event_partner, updated_event_partner, past_event_partner = self.env["res.partner"].create([{
            'name': 'Created Event Partner',
            "email": 'created.event.partner@odoo.com',
        }, {
            "name": 'Updated Event Partner',
            "email": 'updated.event.partner@odoo.com',
        }, {
            "name": 'Past Event Partner',
            "email": 'past.event.partner@odoo.com',
        }])
        past_event = self.env['calendar.event'].with_user(self.user_demo).create({
            'name': 'Past Event',
            'start': '2010-01-01 08:00:00',
        })
        with self.mock_mail_gateway():
            # Check that the modal allowing to send invitations is displayed each time attendees are added to upcoming events.
            self.start_tour(f'/odoo/calendar/calendar.event/{past_event.id}', 'calendar_invite_tour', login='demo')
        # Check that the new attendees receive invitations for the upcoming event.
        self.assertMailMail(created_event_partner, 'sent', author=self.user_demo.partner_id)
        self.assertMailMail(updated_event_partner, 'sent', author=self.user_demo.partner_id)
        self.assertNoMail(past_event_partner)
