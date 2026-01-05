from datetime import datetime, timedelta

from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle
from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBridging(TestSyncGoogle):

    def setUp(self):
        super().setUp()
        self.google_user1 = mail_new_test_user(self.env, login='google_user1', email='g1@google.com')
        self.outlook_user1 = mail_new_test_user(self.env, login='outlook_user1', email='o1@outlook.com')

        self.outlook_user1.microsoft_calendar_sync_token = 'mock_token'

    def test_google_then_microsoft(self):
        """ Test that an event synced from Google first is correctly matched by Microsoft sync. """
        google_id = 'gid_123'
        ical_uid = 'universal_456'

        event_values = {
            'id': google_id,
            'iCalUID': ical_uid,
            'summary': 'Google First Meeting',
            'start': {'dateTime': '2023-01-01T10:00:00Z'},
            'end': {'dateTime': '2023-01-01T11:00:00Z'},
            'organizer': {'email': self.google_user1.email, 'self': True},
            'attendees': [
                {'email': self.google_user1.email, 'responseStatus': 'accepted', 'self': True},
                {'email': self.outlook_user1.email, 'responseStatus': 'needsAction'},
            ],
            'reminders': {'useDefault': True},
            'updated': '2023-01-01T09:00:00Z',
        }
        google_events = GoogleEvent([event_values])
        self.env['calendar.event'].with_user(self.google_user1)._sync_google2odoo(google_events)

        ms_id = 'ms_abc_123'
        ms_event_values = {
            'id': ms_id,
            'iCalUId': ical_uid,
            'subject': 'Google First Meeting',
            'start': {'dateTime': '2023-01-01T10:00:00.0000000Z', 'timeZone': 'UTC'},
            'end': {'dateTime': '2023-01-01T11:00:00.0000000Z', 'timeZone': 'UTC'},
            'showAs': 'busy',
            'isAllDay': False,
            'responseStatus': {'response': 'none'},
            'organizer': {'emailAddress': {'address': self.google_user1.email}},
            'attendees': [
                {'emailAddress': {'address': self.google_user1.email}, 'status': {'response': 'accepted'}},
                {'emailAddress': {'address': self.outlook_user1.email}, 'status': {'response': 'none'}},
            ],
            'lastModifiedDateTime': '2026-01-01T09:05:00Z',
        }
        ms_events = MicrosoftEvent([ms_event_values])
        self.env['calendar.event'].with_user(self.outlook_user1)._sync_microsoft2odoo(ms_events)

        all_events = self.env['calendar.event'].search([('name', '=', 'Google First Meeting')])

        self.assertEqual(len(all_events), 1, "Should NOT have created a duplicate")

        event = all_events[0]
        self.assertEqual(event.name, 'Google First Meeting')
        self.assertEqual(len(event.attendee_ids), 2)

    def test_microsoft_then_google(self):
        """ Test that an event synced from Microsoft first is correctly matched by Google sync. """
        ical_uid = 'universal_789'
        ms_id = 'ms_def_456'

        ms_event_values = {
            'id': ms_id,
            'iCalUId': ical_uid,
            'subject': 'Microsoft First Meeting',
            'start': {'dateTime': '2023-01-01T14:00:00.0000000Z', 'timeZone': 'UTC'},
            'end': {'dateTime': '2023-01-01T15:00:00.0000000Z', 'timeZone': 'UTC'},
            'showAs': 'busy',
            'isAllDay': False,
            'responseStatus': {'response': 'none'},
            'organizer': {'emailAddress': {'address': self.outlook_user1.email}},
            'attendees': [
                {'emailAddress': {'address': self.outlook_user1.email}, 'status': {'response': 'accepted'}},
                {'emailAddress': {'address': self.google_user1.email}, 'status': {'response': 'none'}},
            ],
            'lastModifiedDateTime': '2023-01-01T09:00:00Z',
        }
        ms_events = MicrosoftEvent([ms_event_values])
        self.outlook_user1.microsoft_calendar_token_validity = datetime.now() + timedelta(hours=1)
        self.env['calendar.event'].with_user(self.outlook_user1)._sync_microsoft2odoo(ms_events)

        google_id = 'gid_456'
        event_values = {
            'id': google_id,
            'iCalUID': ical_uid,
            'summary': 'Microsoft First Meeting',
            'start': {'dateTime': '2023-01-01T14:00:00Z'},
            'end': {'dateTime': '2023-01-01T15:00:00Z'},
            'organizer': {'email': self.outlook_user1.email, 'self': False},
            'attendees': [
                {'email': self.outlook_user1.email, 'responseStatus': 'accepted'},
                {'email': self.google_user1.email, 'responseStatus': 'needsAction', 'self': True},
            ],
            'reminders': {'useDefault': True},
            'updated': '2026-01-01T12:00:00Z',
        }
        google_events = GoogleEvent([event_values])
        self.env['calendar.event'].with_user(self.google_user1)._sync_google2odoo(google_events)

        all_events = self.env['calendar.event'].search([('name', '=', 'Microsoft First Meeting')])

        self.assertEqual(len(all_events), 1, "Should NOT have created a duplicate")

        event = all_events[0]
        self.assertEqual(event.name, 'Microsoft First Meeting')
        self.assertEqual(len(event.attendee_ids), 2)
