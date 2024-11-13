# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_calendar.models.res_users import User
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import users, warmup
from odoo.tests import tagged
from odoo import tools

from .test_token_access import TestTokenAccess

@tagged('odoo2google')
@patch.object(User, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncOdoo2Google(TestSyncGoogle):

    def setUp(self):
        super().setUp()
        self.env.user.partner_id.tz = "Europe/Brussels"
        self.google_service = GoogleCalendarService(self.env['google.service'])
        # Make sure this test will work for the next 30 years
        self.env['ir.config_parameter'].set_param('google_calendar.sync.range_days', 10000)

    @patch_api
    def test_event_creation(self):
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        alarm = self.env['calendar.alarm'].create({
            'name': 'Notif',
            'alarm_type': 'notification',
            'interval': 'minutes',
            'duration': 18,
        })
        description = '<script>alert("boom")</script><p style="white-space: pre"><h1>HELLO</h1></p><ul><li>item 1</li><li>item 2</li></ul>'
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
            'partner_ids': [(4, partner.id)],
            'alarm_ids': [(4, alarm.id)],
            'privacy': 'private',
            'need_sync': False,
            'description': description,
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'dateTime': '2020-01-15T08:00:00+00:00', 'date': None},
            'end': {'dateTime': '2020-01-15T18:00:00+00:00', 'date': None},
            'summary': 'Event',
            'description': tools.html_sanitize(description),
            'location': '',
            'visibility': 'private',
            'guestsCanModify': True,
            'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': alarm.duration_minutes}]},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'jean-luc@opoo.com', 'responseStatus': 'needsAction'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'transparency': 'opaque',
        })

    @patch_api
    @users('__system__')
    @warmup
    def test_event_creation_perf(self):
        EVENT_COUNT = 100
        partners = self.env['res.partner'].create([
            {'name': 'Jean-Luc %s' % (i), 'email': 'jean-luc-%s@opoo.com' % (i)} for i in range(EVENT_COUNT)])
        alarm = self.env['calendar.alarm'].create({
            'name': 'Notif',
            'alarm_type': 'notification',
            'interval': 'minutes',
            'duration': 18,
        })
        partner_model = self.env.ref('base.model_res_partner')
        partner = self.env['res.partner'].search([], limit=1)
        with self.assertQueryCount(__system__=615):
            events = self.env['calendar.event'].create([{
                'name': "Event %s" % (i),
                'start': datetime(2020, 1, 15, 8, 0),
                'stop': datetime(2020, 1, 15, 18, 0),
                'partner_ids': [(4, partners[i].id), (4, self.env.user.partner_id.id)],
                'alarm_ids': [(4, alarm.id)],
                'privacy': 'private',
                'need_sync': False,
                'res_model_id': partner_model.id,
                'res_id': partner.id,
            } for i in range(EVENT_COUNT)])

            events._sync_odoo2google(self.google_service)

        with self.assertQueryCount(__system__=28):
            events.unlink()


    @patch_api
    @users('__system__')
    @warmup
    def test_recurring_event_creation_perf(self):
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        alarm = self.env['calendar.alarm'].create({
            'name': 'Notif',
            'alarm_type': 'notification',
            'interval': 'minutes',
            'duration': 18,
        })
        partner_model = self.env.ref('base.model_res_partner')
        partner = self.env['res.partner'].search([], limit=1)
        with self.assertQueryCount(__system__=86):
            event = self.env['calendar.event'].create({
                'name': "Event",
                'start': datetime(2020, 1, 15, 8, 0),
                'stop': datetime(2020, 1, 15, 18, 0),
                'partner_ids': [(4, partner.id)],
                'alarm_ids': [(4, alarm.id)],
                'privacy': 'private',
                'need_sync': False,
                'interval': 1,
                'recurrency': True,
                'rrule_type': 'daily',
                'end_type': 'forever',
                'res_model_id': partner_model.id,
                'res_id': partner.id,
            })

        with self.assertQueryCount(__system__=38):
            event.unlink()

    def test_event_without_user(self):
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
            'user_id': False,
            'privacy': 'private',
            'need_sync': False,
        })
        values = event._google_values()
        self.assertFalse('%s_owner_id' % self.env.cr.dbname in values.get('extendedProperties', {}).get('shared', {}))

    @patch_api
    def test_event_without_attendee_state(self):
        partner_1 = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        partner_2 = self.env['res.partner'].create({'name': 'Phineas', 'email': 'phineas@opoo.com'})
        partner_3 = self.env['res.partner'].create({'name': 'Ferb'})
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
            'partner_ids': [(4, partner_1.id), (4, partner_2.id), (4, partner_3.id)],
            'privacy': 'private',
            'need_sync': False,
        })
        attendee_2 = event.attendee_ids.filtered(lambda a: a.partner_id.id == partner_2.id)
        attendee_2.write({
            'state': False,
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'dateTime': '2020-01-15T08:00:00+00:00', 'date': None},
            'end': {'dateTime': '2020-01-15T18:00:00+00:00', 'date': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'visibility': 'private',
            'guestsCanModify': True,
            'reminders': {'useDefault': False, 'overrides': []},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'jean-luc@opoo.com', 'responseStatus': 'needsAction'},
                          {'email': 'phineas@opoo.com', 'responseStatus': 'needsAction'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'transparency': 'opaque',
        })

    @patch_api
    def test_event_allday_creation(self):
        event = self.env['calendar.event'].create({
            'name': "Event",
            'allday': True,
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'need_sync': False,
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'date': '2020-01-15', 'dateTime': None},
            'end': {'date': '2020-01-16', 'dateTime': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'transparency': 'opaque',
        })

    @patch_api
    def test_inactive_event(self):
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'active': False,
            'need_sync': False,
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventNotInserted()
        self.assertGoogleEventNotDeleted()

    @patch_api
    def test_synced_inactive_event(self):
        google_id = 'aaaaaaaaa'
        # writing on synced event will put it in a need_sync state.
        # Delete api will not be called but the state of the event will be set as 'cancelled'
        event = self.env['calendar.event'].create({
            'google_id': google_id,
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'active': False,
            'need_sync': True,
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventDeleted(google_id)

    @patch_api
    def test_recurrence(self):
        google_id = 'aaaaaaaaa'
        event = self.env['calendar.event'].create({
            'google_id': google_id,
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=WE',
            'calendar_event_ids': [(4, event.id)],
            'need_sync': False,
        })
        recurrence._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'date': '2020-01-15', 'dateTime': None},
            'end': {'date': '2020-01-16', 'dateTime': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=WE'],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: recurrence.id}},
            'transparency': 'opaque',
        })

    @patch_api
    def test_event_added_to_recurrence(self):
        google_id = 'aaaaaaaaa'
        event = self.env['calendar.event'].create({
            'google_id': google_id,
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'need_sync': False,
        })
        event.write({
            'recurrency': True,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=WE',
        })
        to_delete = self.env['calendar.event'].with_context(active_test=False).search([('google_id', '=', google_id)])
        self.assertTrue(to_delete)
        self.assertFalse(to_delete.active)
        self.assertFalse(event.google_id, "The google id will be set after the API call")
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'date': '2020-01-15', 'dateTime': None},
            'end': {'date': '2020-01-16', 'dateTime': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=WE'],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.recurrence_id.id}},
            'transparency': 'opaque',
        }, timeout=3)

        self.assertGoogleEventDeleted(google_id)

    @patch_api
    def test_following_event_updated(self):
        google_id = 'aaaaaaaaa'
        event_1 = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'need_sync': False,
        })
        event_2 = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 22),
            'stop': datetime(2020, 1, 22),
            'allday': True,
            'need_sync': False,
        })
        self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=WE',
            'calendar_event_ids': [(4, event_1.id), (4, event_2.id)],
            'need_sync': False,
        })
        event = event_2

        # Update only some events in the recurrence
        event.write({
            'name': 'New name',
            'recurrence_update': 'future_events',
        })
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'date': str(event.start_date), 'dateTime': None},
            'end': {'date': str(event.stop_date + relativedelta(days=1)), 'dateTime': None},
            'summary': 'New name',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.recurrence_id.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=1;BYDAY=WE'],
            'transparency': 'opaque',
        }, timeout=3)

    @patch_api
    def test_stop_synchronization(self):
        self.env.user.stop_google_synchronization()
        self.assertTrue(self.env.user.google_synchronization_stopped, "The google synchronization flag should be switched on")
        self.assertFalse(self.env.user._sync_google_calendar(self.google_service), "The google synchronization should be stopped")

        # If synchronization stopped, creating a new event should not call _google_insert.
        self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
            'privacy': 'private',
        })
        self.assertGoogleEventNotInserted()

    @patch_api
    def test_restart_synchronization(self):
        # Test new event created after stopping synchronization are correctly patched when restarting sync.
        google_id = 'aaaaaaaaa'
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        user = self.env['res.users'].create({
            'name': 'Test user Calendar',
            'login': 'jean-luc@opoo.com',
            'partner_id': partner.id,
        })
        user.stop_google_synchronization()
        event = self.env['calendar.event'].with_user(user).create({
            'google_id': google_id,
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
            'partner_ids': [(4, partner.id)],
        })

        user.with_user(user).restart_google_synchronization()
        self.assertGoogleEventPatched(event.google_id, {
            'id': event.google_id,
            'start': {'dateTime': '2020-01-15T08:00:00+00:00', 'date': None},
            'end': {'dateTime': '2020-01-15T18:00:00+00:00', 'date': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'jean-luc@opoo.com', 'self': True},
            'attendees': [{'email': 'jean-luc@opoo.com', 'responseStatus': 'accepted'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'transparency': 'opaque',
        }, timeout=3)

    @patch_api
    def test_all_event_updated(self):
        google_id = 'aaaaaaaaa'
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=WE',
            'base_event_id': event.id,
            'need_sync': False,
        })
        recurrence._apply_recurrence()
        event.write({
            'name': 'New name',
            'recurrence_update': 'all_events',
        })
        new_recurrence = self.env['calendar.recurrence'].search([('id', '>', recurrence.id)])
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'date': str(event.start_date), 'dateTime': None},
            'end': {'date': str(event.stop_date + relativedelta(days=1)), 'dateTime': None},
            'summary': 'New name',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=2;BYDAY=WE'],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: new_recurrence.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'transparency': 'opaque',
        }, timeout=3)

    @patch_api
    def test_event_need_sync(self):
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'recurrence_id': False,
            'recurrency': True,
        })
        self.assertFalse(event.need_sync,
                         "Event created with True recurrency should not be synched to avoid "
                         "duplicate event on google")

        recurrence = self.env['calendar.recurrence'].create({
            'google_id': False,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=WE',
            'base_event_id': event.id,
            'need_sync': False,
        })
        event_2 = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'recurrence_id': recurrence.id,
        })
        self.assertFalse(event_2.need_sync,
                         "Event created with recurrence_id should not be synched to avoid "
                         "duplicate event on google")

        self.assertGoogleEventNotInserted()
        self.assertGoogleEventNotDeleted()


    @patch_api
    def test_event_until_utc(self):
        """ UNTIl rrule value must be in UTC: ending with a 'Z """
        google_id = 'aaaaaaaaa'
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=DAILY;UNTIL=20200117T235959',
            'base_event_id': event.id,
            'need_sync': False,
        })
        recurrence._apply_recurrence()
        self.assertEqual(recurrence._google_values()['recurrence'][0], 'RRULE:FREQ=DAILY;UNTIL=20200117T235959Z',
                         "The rrule sent to google should be in UTC: end with Z")
        # Add it even if it is not the end of the string
        recurrence.write({'rrule': 'FREQ=DAILY;UNTIL=20200118T235959;INTERVAL=3'})
        recurrence._apply_recurrence()
        self.assertEqual(recurrence._google_values()['recurrence'][0],
                         'RRULE:FREQ=DAILY;UNTIL=20200118T235959Z;INTERVAL=3',
                         "The rrule sent to google should be in UTC: end with Z and preserve the following parameters")
        # Don't add two Z at the end of the UNTIL value
        recurrence.write({'rrule': 'FREQ=DAILY;UNTIL=20200119T235959Z'})
        recurrence._apply_recurrence()
        self.assertEqual(recurrence._google_values()['recurrence'][0], 'RRULE:FREQ=DAILY;UNTIL=20200119T235959Z',
                         "The rrule sent to google should be in UTC: end with one Z")

    @patch_api
    def test_write_unsynced_field(self):
        google_id = 'aaaaaaaaa'
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2021, 3, 10),
            'stop': datetime(2021, 3, 10),
            'allday': True,
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=WE',
            'base_event_id': event.id,
            'need_sync': False,
        })
        recurrence._apply_recurrence()
        event.write({
            'start': datetime(2021, 3, 11),
            'stop': datetime(2021, 3, 11),
            'need_sync': False,
        })
        event_type = self.env['calendar.event.type'].create({'name': 'type'})
        event.write({
            'recurrence_update': 'all_events',
            'categ_ids': [(4, event_type.id)]
        })
        self.assertTrue(all(e.categ_ids == event_type for e in recurrence.calendar_event_ids))
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_attendee_state(self):
        """ Sync attendee state immediately """
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        event = self.env['calendar.event'].create({
            'name': "Event with attendees",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'need_sync': False,
            'partner_ids': [(4, partner.id)],
            'google_id': 'aaaaaaaaa',
        })
        self.assertEqual(event.attendee_ids.state, 'needsAction',
                         "The attendee state should be 'needsAction")

        event.attendee_ids.do_decline()
        self.assertGoogleEventPatched(event.google_id, {
            'id': event.google_id,
            'start': {'date': str(event.start_date), 'dateTime': None},
            'end': {'date': str(event.stop_date + relativedelta(days=1)), 'dateTime': None},
            'summary': 'Event with attendees',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'jean-luc@opoo.com', 'responseStatus': 'declined'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'transparency': 'opaque',
        })


    @patch_api
    def test_all_event_with_tz_updated(self):
        google_id = 'aaaaaaaaa'
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 9, 0),
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=WE',
            'base_event_id': event.id,
            'need_sync': False,
        })
        recurrence._apply_recurrence()
        event.write({
            'name': 'New name',
            'recurrence_update': 'all_events',
        })
        new_recurrence = self.env['calendar.recurrence'].search([('id', '>', recurrence.id)])
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'dateTime': "2020-01-15T08:00:00+00:00", 'timeZone': 'Europe/Brussels', 'date': None},
            'end': {'dateTime': "2020-01-15T09:00:00+00:00", 'timeZone': 'Europe/Brussels', 'date': None},
            'summary': 'New name',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=2;BYDAY=WE'],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: new_recurrence.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'transparency': 'opaque',
        }, timeout=3)

    def test_send_update_do_request(self):
        self.env.cr.postcommit.clear()
        with self.mock_google_service():
            event = self.env['calendar.event'].create({
                'name': "Event",
                'allday': True,
                'start': datetime(2020, 1, 15),
                'stop': datetime(2020, 1, 15),
                'need_sync': False,
            })
            event.with_context(send_updates=True)._sync_odoo2google(self.google_service)
            self.call_post_commit_hooks()
        self.assertGoogleEventSendUpdates('all')

    def test_not_send_update_do_request(self):
        with self.mock_google_service():
            event = self.env['calendar.event'].create({
                'name': "Event",
                'allday': True,
                'start': datetime(2020, 1, 15),
                'stop': datetime(2020, 1, 15),
                'need_sync': False,
            })
            event.with_context(send_updates=False)._sync_odoo2google(self.google_service)
            self.call_post_commit_hooks()
        self.assertGoogleEventSendUpdates('none')

    @patch_api
    def test_recurrence_delete_single_events(self):
        """
        Creates a recurrence with two events, deletes the events and assert that the recurrence was updated.
        """
        # Setup recurrence with two recurrences (event_1 as the recurrence base_event).
        google_id = 'aaaaaaaaa'
        event_1 = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2023, 6, 15, 10, 0),
            'stop': datetime(2023, 6, 15, 10, 0),
            'need_sync': False,
        })
        event_2 = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2023, 6, 22, 10, 0),
            'stop': datetime(2023, 6, 22, 10, 0),
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=TH',
            'base_event_id': event_1.id,
            'calendar_event_ids': [(4, event_1.id), (4, event_2.id)],
            'need_sync': False,
        })
        # Delete base_event and assert that patch was called.
        event_1.action_mass_archive('self_only')
        self.assertGoogleEventPatched(event_1.google_id, {
            'id': event_1.google_id,
            'start': {'dateTime': '2023-06-15T10:00:00+00:00', 'date': None},
            'end': {'dateTime': '2023-06-15T10:00:00+00:00', 'date': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event_1.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'status': 'cancelled',
            'transparency': 'opaque',
        }, timeout=3)
        # Assert that deleted event is not active anymore and the recurrence updated its calendar_event_ids.
        self.assertFalse(event_1.active)
        self.assertEqual(recurrence.base_event_id.id, event_2.id)
        self.assertEqual(recurrence.calendar_event_ids.ids, [event_2.id])
        # Delete last event and assert that the recurrence and event were archived after the last event deletion.
        event_2.action_mass_archive('self_only')
        self.assertFalse(event_2.active)
        self.assertFalse(recurrence.active)

    @patch_api
    def test_create_event_with_sync_config_paused(self):
        """
        Creates an event with the synchronization paused, its field 'need_sync'
        must be True for later synchronizing it with Google Calendar.
        """
        # Set synchronization as active and unpause the synchronization.
        self.env.user.google_synchronization_stopped = False
        self.env.user.sudo().pause_google_synchronization()

        # Create record and call synchronization method.
        record = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2023, 6, 29, 8, 0),
            'stop': datetime(2023, 6, 29, 18, 0),
            'need_sync': True
        })
        record._sync_odoo2google(self.google_service)

        # Assert that synchronization is paused, insert wasn't called and record is waiting to be synced.
        self.assertFalse(self.env.user.google_synchronization_stopped)
        self.assertEqual(self.env.user._get_google_sync_status(), "sync_paused")
        self.assertTrue(record.need_sync, "Sync variable must be true for updating event when sync re-activates")
        self.assertGoogleEventNotInserted()

    @patch_api
    def test_update_synced_event_with_sync_config_paused(self):
        """
        Updates a synced event with synchronization paused, event must be modified and have its
        field 'need_sync' as True for later synchronizing it with Google Calendar.
        """
        # Set synchronization as active and unpause it.
        self.env.user.google_synchronization_stopped = False
        self.env.user.sudo().unpause_google_synchronization()

        # Setup synced record in Calendar.
        record = self.env['calendar.event'].create({
            'google_id': 'aaaaaaaaa',
            'name': "Event",
            'start': datetime(2023, 6, 29, 8, 0),
            'stop': datetime(2023, 6, 29, 18, 0),
            'need_sync': False
        })

        # Pause synchronization and update synced event. It will only update it locally.
        self.env.user.sudo().pause_google_synchronization()
        record.write({'name': "Updated Event"})
        record._sync_odoo2google(self.google_service)

        # Assert that synchronization is paused, patch wasn't called and record is waiting to be synced.
        self.assertFalse(self.env.user.google_synchronization_stopped)
        self.assertEqual(self.env.user._get_google_sync_status(), "sync_paused")
        self.assertEqual(record.name, "Updated Event", "Assert that event name was updated in Odoo Calendar")
        self.assertTrue(record.need_sync, "Sync variable must be true for updating event when sync re-activates")
        self.assertGoogleEventNotPatched()

    @patch_api
    def test_delete_synced_event_with_sync_config_paused(self):
        """
        Deletes a synced event with synchronization paused, event must be archived in Odoo and
        have its field 'need_sync' as True for later synchronizing it with Google Calendar.
        """
        # Set synchronization as active and then pause synchronization.
        self.env.user.google_synchronization_stopped = False
        self.env.user.sudo().unpause_google_synchronization()

        # Setup synced record in Calendar.
        record = self.env['calendar.event'].create({
            'google_id': 'aaaaaaaaa',
            'name': "Event",
            'start': datetime(2023, 6, 29, 8, 0),
            'stop': datetime(2023, 6, 29, 18, 0),
            'need_sync': False
        })

        # Pause synchronization and delete synced event.
        self.env.user.sudo().pause_google_synchronization()
        record.unlink()

        # Assert that synchronization is paused, delete wasn't called and record was archived in Odoo.
        self.assertFalse(self.env.user.google_synchronization_stopped)
        self.assertEqual(self.env.user._get_google_sync_status(), "sync_paused")
        self.assertFalse(record.active, "Event must be archived in Odoo after unlinking it")
        self.assertTrue(record.need_sync, "Sync variable must be true for updating event in Google when sync re-activates")
        self.assertGoogleEventNotDeleted()

    @patch_api
    def test_videocall_location_on_location_set(self):
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
            'partner_ids': [(4, partner.id)],
            'need_sync': False,
            'location' : 'Event Location'
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({'conferenceData': False})

    @patch_api
    def test_event_available_privacy(self):
        """ Create an event with "Available" value for 'show_as' and assert value is properly sync in google calendar. """
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2024, 3, 29, 10, 0),
            'stop': datetime(2024, 3, 29, 10, 0),
            'need_sync': False,
            'show_as': 'free'
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'dateTime': '2024-03-29T10:00:00+00:00', 'date': None},
            'end': {'dateTime': '2024-03-29T10:00:00+00:00', 'date': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'transparency': 'transparent',
        })

    @patch_api
    def test_event_busy_privacy(self):
        """ Create an event with "busy" value for 'show_as' and assert value is properly sync in google calendar. """
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2024, 3, 29, 10, 0),
            'stop': datetime(2024, 3, 29, 10, 0),
            'need_sync': False,
            'show_as': 'busy'
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'dateTime': '2024-03-29T10:00:00+00:00', 'date': None},
            'end': {'dateTime': '2024-03-29T10:00:00+00:00', 'date': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'transparency': 'opaque',
        })

    @patch_api
    @patch.object(User, '_sync_request')
    def test_event_sync_after_pause_period(self, mock_sync_request):
        """ Ensure that an event created during the paused synchronization period gets synchronized after resuming it. """
        # Pause the synchronization and creates the local event.
        self.organizer_user.google_synchronization_stopped = False
        self.organizer_user.sudo().pause_google_synchronization()
        record = self.env['calendar.event'].with_user(self.organizer_user).create({
            'name': "Event",
            'start': datetime(2023, 1, 15, 8, 0),
            'stop': datetime(2023, 1, 15, 18, 0),
            'partner_ids': [(4, self.organizer_user.partner_id.id), (4, self.attendee_user.partner_id.id)]
        })

        # Define mock return values for the '_sync_request' method.
        mock_sync_request.return_value = {
            'events': GoogleEvent([]),
            'default_reminders': (),
            'full_sync': False,
        }

        # With the synchronization paused, manually call the synchronization to simulate the page refresh.
        self.organizer_user.sudo()._sync_google_calendar(self.google_service)
        self.assertFalse(self.organizer_user.google_synchronization_stopped, "Synchronization should not be stopped, only paused.")
        self.assertEqual(self.organizer_user._get_google_sync_status(), "sync_paused", "Synchronization must be paused since it wasn't resumed yet.")
        self.assertTrue(record.need_sync, "Record must have its 'need_sync' variable as true for it to be synchronized when the synchronization is resumed.")
        self.assertGoogleEventNotInserted()

        # Unpause the synchronization and call the calendar synchronization. Ensure the event was inserted in Google side.
        self.organizer_user.sudo().unpause_google_synchronization()
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_google_calendar(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'dateTime': '2023-01-15T08:00:00+00:00', 'date': None},
            'end': {'dateTime': '2023-01-15T18:00:00+00:00', 'date': None},
            'summary': 'Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'transparency': 'opaque',
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': self.organizer_user.email, 'self': True},
            'attendees': [
                            {'email': self.attendee_user.email, 'responseStatus': 'needsAction'},
                            {'email': self.organizer_user.email, 'responseStatus': 'accepted'}
                         ],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: record.id}},
        })

    @patch_api
    def test_allday_duplicated_first_event_in_recurrence(self):
        """ Ensure that when creating recurrence with 'all day' events the first event won't get duplicated in Google. """
        # Create 'all day' event: ensure that 'need_sync' is falsy after creation an API wasn't called.
        event = self.env['calendar.event'].with_user(self.organizer_user).create({
            'name': "All Day Recurrent Event",
            'user_id': self.organizer_user.id,
            'start': datetime(2024, 1, 17),
            'stop': datetime(2024, 1, 17),
            'allday': True,
            'need_sync': False,
            'recurrency': True,
            'recurrence_id': False,
        })
        self.assertFalse(event.need_sync, "Variable 'need_sync' must be falsy after event's 'create' call.")
        self.assertGoogleAPINotCalled()

        # Link recurrence to the event: ensure that it got synchronized after creation and API called insert once.
        recurrence = self.env['calendar.recurrence'].with_user(self.organizer_user).create({
            'rrule': 'FREQ=WEEKLY;COUNT=1;BYDAY=WE',
            'calendar_event_ids': [(4, event.id)],
            'need_sync': True,
        })
        self.assertFalse(event.need_sync, "Variable 'need_sync' must be falsy after recurrence's 'create' call.")
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'date': '2024-01-17', 'dateTime': None},
            'end': {'date': '2024-01-18', 'dateTime': None},
            'summary': 'All Day Recurrent Event',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': self.organizer_user.email, 'self': True},
            'attendees': [{'email': self.organizer_user.email, 'responseStatus': 'accepted'}],
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=1;BYDAY=WE'],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: recurrence.id}},
            'transparency': 'opaque',
        }, timeout=3)


@tagged('odoo2google')
class TestSyncOdoo2GoogleMail(TestTokenAccess, TestSyncGoogle, MailCommon):

    @patch.object(User, '_get_google_calendar_token', lambda user: user.google_calendar_token)
    @freeze_time("2020-01-01")
    def test_event_creation_for_user(self):
        organizer1 = self.users[0]
        organizer2 = self.users[1]
        user_root = self.env.ref('base.user_root')
        organizer1.google_calendar_token = 'abc'
        organizer2.google_calendar_token = False
        event_values = {
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
        }
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        for create_user, organizer, responsible, expect_mail, is_public in [
            (user_root, organizer1, organizer1, False, True), (user_root, None, user_root, True, True),
                (organizer1, None, organizer1, False, False), (organizer1, organizer2, organizer1, False, True)]:
            with self.subTest(create_uid=create_user.name if create_user else None, user_id=organizer.name if organizer else None):
                with self.mock_mail_gateway(), self.mock_google_sync(user_id=responsible):
                    self.env['calendar.event'].with_user(create_user).create({
                        **event_values,
                        'partner_ids': [(4, partner.id)],
                        'user_id': organizer.id if organizer else False,
                    })
                if not expect_mail:
                    self.assertNotSentEmail()
                    self.assertGoogleEventInserted({
                        'attendees': [{'email': 'jean-luc@opoo.com', 'responseStatus': 'needsAction'}],
                        'id': False,
                        'start': {'dateTime': '2020-01-15T08:00:00+00:00', 'date': None},
                        'end': {'dateTime': '2020-01-15T18:00:00+00:00', 'date': None},
                        'guestsCanModify': is_public,
                        'organizer': {'email': organizer.email, 'self': False} if organizer else False,
                        'summary': 'Event',
                        'reminders': {'useDefault': False, 'overrides': []},
                    }, timeout=3)
                else:
                    self.assertGoogleEventNotInserted()
                    self.assertMailMail(partner, 'sent', author=user_root.partner_id)
