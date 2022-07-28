# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from unittest.mock import MagicMock, patch

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_account.models.google_service import GoogleService
from odoo.addons.google_calendar.models.res_users import User
from odoo.addons.google_calendar.models.google_sync import GoogleSync
from odoo.modules.registry import Registry
from odoo.addons.google_account.models.google_service import TIMEOUT
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api


@patch.object(User, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncOdoo2Google(TestSyncGoogle):

    def setUp(self):
        super().setUp()
        self.google_service = GoogleCalendarService(self.env['google.service'])

    @patch_api
    def test_event_creation(self):
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        alarm = self.env['calendar.alarm'].create({
            'name': 'Notif',
            'alarm_type': 'notification',
            'interval': 'minutes',
            'duration': 18,
        })
        event = self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
            'partner_ids': [(4, partner.id)],
            'alarm_ids': [(4, alarm.id)],
            'privacy': 'private',
            'need_sync': False,
        })
        event._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'start': {'dateTime': '2020-01-15T08:00:00+00:00'},
            'end': {'dateTime': '2020-01-15T18:00:00+00:00'},
            'summary': 'Event',
            'description': '',
            'location': '',
            'visibility': 'private',
            'guestsCanModify': True,
            'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': alarm.duration_minutes}]},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [{'email': 'jean-luc@opoo.com', 'responseStatus': 'needsAction'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}}
        })

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
            'start': {'date': '2020-01-15'},
            'end': {'date': '2020-01-16'},
            'summary': 'Event',
            'description': '',
            'location': '',
            'visibility': 'public',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}}
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
        event = self.env['calendar.event'].create({
            'google_id': google_id,
            'name': "Event",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'active': False,
            'need_sync': False,
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
            'start': {'date': '2020-01-15'},
            'end': {'date': '2020-01-16'},
            'summary': 'Event',
            'description': '',
            'location': '',
            'visibility': 'public',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [],
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=WE'],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: recurrence.id}}
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
            'start': {'date': '2020-01-15'},
            'end': {'date': '2020-01-16'},
            'summary': 'Event',
            'description': '',
            'location': '',
            'visibility': 'public',
            'guestsCanModify': True,
            'reminders': {'overrides': [], 'useDefault': False},
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [],
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=WE'],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.recurrence_id.id}}
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
        self.assertGoogleEventPatched(event.google_id, {
            'id': event.google_id,
            'start': {'date': str(event.start_date)},
            'end': {'date': str(event.stop_date + relativedelta(days=1))},
            'summary': 'New name',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'visibility': 'public',
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
        self.assertGoogleEventPatched(recurrence.google_id, {
            'id': recurrence.google_id,
            'start': {'date': str(event.start_date)},
            'end': {'date': str(event.stop_date + relativedelta(days=1))},
            'summary': 'New name',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'attendees': [],
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=WE'],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: recurrence.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'visibility': 'public',
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
            "Sync attendee state immediately"
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

            event.attendee_ids.write({'state': 'declined'})
            self.assertGoogleEventPatched(event.google_id, {
                'id': event.google_id,
                'start': {'date': str(event.start_date)},
                'end': {'date': str(event.stop_date + relativedelta(days=1))},
                'summary': 'Event with attendees',
                'description': '',
                'location': '',
                'guestsCanModify': True,
                'organizer': {'email': 'odoobot@example.com', 'self': True},
                'attendees': [{'email': 'jean-luc@opoo.com', 'responseStatus': 'declined'}],
                'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
                'reminders': {'overrides': [], 'useDefault': False},
                'visibility': 'public',
            })

    @patch.object(GoogleService, '_do_request')
    def test_send_update_do_request(self, mock_do_request):
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

    @patch.object(GoogleService, '_do_request')
    def test_not_send_update_do_request(self, mock_do_request):
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
