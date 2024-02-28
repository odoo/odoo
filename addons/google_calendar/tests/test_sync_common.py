# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import time

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService, GoogleEvent
from odoo.addons.google_account.models.google_service import GoogleService
from odoo.addons.google_calendar.models.res_users import User
from odoo.addons.google_calendar.models.google_sync import GoogleSync
from odoo.tests.common import HttpCase, new_test_user
from odoo import Command
from freezegun import freeze_time
from contextlib import contextmanager


def patch_api(func):
    @patch.object(GoogleSync, '_google_insert', MagicMock(spec=GoogleSync._google_insert))
    @patch.object(GoogleSync, '_google_delete', MagicMock(spec=GoogleSync._google_delete))
    @patch.object(GoogleSync, '_google_patch', MagicMock(spec=GoogleSync._google_patch))
    def patched(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return patched

@patch.object(User, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncGoogle(HttpCase):

    def setUp(self):
        super().setUp()
        self.google_service = GoogleCalendarService(self.env['google.service'])
        self.organizer_user = new_test_user(self.env, login="organizer_user")
        self.attendee_user = new_test_user(self.env, login='attendee_user')

    @contextmanager
    def mock_datetime_and_now(self, mock_dt):
        """ Used when synchronization date (using env.cr.now()) is important
        in addition to standard datetime mocks. Used mainly to detect sync
        issues. """
        with freeze_time(mock_dt), \
                patch.object(self.env.cr, 'now', lambda: mock_dt):
            yield

    def assertGoogleEventDeleted(self, google_id):
        GoogleSync._google_delete.assert_called()
        args, dummy = GoogleSync._google_delete.call_args
        self.assertEqual(args[1], google_id, "Event should have been deleted")

    def assertGoogleEventNotDeleted(self):
        GoogleSync._google_delete.assert_not_called()

    def assertGoogleEventInserted(self, values, timeout=None):
        expected_args = (values,)
        expected_kwargs = {'timeout': timeout} if timeout else {}
        GoogleSync._google_insert.assert_called_once()
        args, kwargs = GoogleSync._google_insert.call_args
        args[1:][0].pop('conferenceData', None)
        self.assertEqual(args[1:], expected_args) # skip Google service arg
        self.assertEqual(kwargs, expected_kwargs)

    def assertGoogleEventNotInserted(self):
        GoogleSync._google_insert.assert_not_called()

    def assertGoogleEventPatched(self, google_id, values, timeout=None):
        expected_args = (google_id, values)
        expected_kwargs = {'timeout': timeout} if timeout else {}
        GoogleSync._google_patch.assert_called_once()
        args, kwargs = GoogleSync._google_patch.call_args
        self.assertEqual(args[1:], expected_args) # skip Google service arg
        self.assertEqual(kwargs, expected_kwargs)

    def assertGoogleEventNotPatched(self):
        GoogleSync._google_patch.assert_not_called()

    def assertGoogleAPINotCalled(self):
        self.assertGoogleEventNotPatched()
        self.assertGoogleEventNotInserted()
        self.assertGoogleEventNotDeleted()

    def assertGoogleEventSendUpdates(self, expected_value):
        GoogleService._do_request.assert_called_once()
        args, _ = GoogleService._do_request.call_args
        val = "sendUpdates=%s" % expected_value
        self.assertTrue(val in args[0], "The URL should contain %s" % val)

    def call_post_commit_hooks(self):
        """
        manually calls postcommit hooks defined with the decorator @after_commit
        """

        funcs = self.env.cr.postcommit._funcs.copy()
        while funcs:
            func = funcs.popleft()
            func()

    def assertGoogleEventHasNoConferenceData(self):
        GoogleSync._google_insert.assert_called_once()
        args, _ = GoogleSync._google_insert.call_args
        self.assertFalse(args[1].get('conferenceData', False))

    def generate_recurring_event(self, mock_dt, google_id):
        with self.mock_datetime_and_now(mock_dt):
            base_event = self.env['calendar.event'].with_user(self.organizer_user).create({
                'name': 'coucou',
                'start': datetime(2024, 3, 20, 9, 0),
                'stop': datetime(2024, 3, 20, 10, 0),
                'need_sync': False,
                'partner_ids': [Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])]
            })
            recurrence = self.env['calendar.recurrence'].with_user(self.organizer_user).create({
                'google_id': google_id,
                'rrule': 'FREQ=DAILY;INTERVAL=1;COUNT=4',
                'need_sync': False,
                'base_event_id': base_event.id,
            })
            recurrence._apply_recurrence()
        return recurrence

    def accept_recurring_event_google_update(self, recurrence_id, update_time, option):
        """
        This method simulates what we get from google when accepting a recurring event on google calendar.
        In case option == "single event" or "This and following events" we start from the third event.
        """
        event1 = {
            "id": recurrence_id,
            "updated": update_time,
            "organizer": {"email": self.organizer_user.partner_id.email},
            "summary": "coucou",
            "visibility": "public",
            "attendees": [
                {
                    "email": self.organizer_user.partner_id.email,
                    "responseStatus": "accepted",
                },
                {
                    "email": self.attendee_user.partner_id.email,
                    "responseStatus": "accepted",
                },
            ],
            "recurrence": ["RRULE:FREQ=DAILY;INTERVAL=1;COUNT=4"],
            "reminders": {"useDefault": True},
            "start": {
                "dateTime": "2024-03-20T09:00:00+00:00",
            },
            "end": {
                "dateTime": "2024-03-20T10:00:00+00:00",
            },
        }
        if option == "all events":
            return [event1]
        event2 = event1.copy()
        event1['attendees'] = [
            {"email": self.organizer_user.partner_id.email, "responseStatus": "accepted"},
            {"email": self.attendee_user.partner_id.email, "responseStatus": "needsAction"}
        ]
        event2["start"] = {
            "dateTime": "2024-03-22T09:00:00+00:00",
        }
        event2["end"] = {
            "dateTime": "2024-03-22T010:00:00+00:00",
        }
        event2.pop("recurrence")
        if option == "single event":
            event2['id'] = "%s_20240322T090000Z" % recurrence_id
            event2['recurringEventId'] = recurrence_id
            event2['attendees'][1]['responseStatus'] = "accepted"
            return [event1, event2]

        # otherwise we accept the third event with option "this event and following events"
        event1['recurrence'] = [
            "RRULE:FREQ=DAILY;UNTIL=20240321T215959Z"
        ]
        event2['id'] = "%s_R20240322T090000Z" % recurrence_id
        event2['recurrence'] = [
            "RRULE:FREQ=DAILY;COUNT=2"
        ]
        return [event1, event2]

    @patch.object(GoogleCalendarService, 'get_events')
    def test_accepting_recurring_events(self, mock_get_events):
        id_suffix = "x"
        recurrence_id = "abcd"
        expected_response = [
            {"single event": "needsAction", "all events": "accepted", "This event and following events": "needsAction"},
            {"single event": "needsAction", "all events": "accepted", "This event and following events": "needsAction"},
            {"single event": "accepted", "all events": "accepted"},
            {"single event": "needsAction", "all events": "accepted"}
        ]
        for option in ["single event", "all events", "This event and following events"]:
            for user in [self.attendee_user, self.organizer_user]:
                recurrence_id = "%s%s" % (recurrence_id, id_suffix)
                recurrence = self.generate_recurring_event("2024-04-20", recurrence_id)
                update_time = (recurrence.write_date + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
                google_events = self.accept_recurring_event_google_update(recurrence_id, update_time, option)
                mock_get_events.return_value = (
                    GoogleEvent(google_events), None, [{'method': 'popup', 'minutes': 30}]
                )
                with self.mock_datetime_and_now("2024-04-22"):
                    user.sudo()._sync_google_calendar(self.google_service)
                    events = recurrence.calendar_event_ids.sorted("start")
                    for i in range(len(events)):
                        self.assertEqual(events[i].attendee_ids[1].state, expected_response[i][option], "Failed at option %s when syncing %s at event number %s" % (option, user.login, i))
                    if option == "This event and following events":
                        recurrence2 = self.env['calendar.recurrence'].search([
                            ('google_id', '=', ("%s_R20240322T090000Z" % recurrence_id))
                        ])
                        for event in recurrence2.calendar_event_ids:
                            self.assertEqual(event.attendee_ids[1].state, "accepted", "Failed at option %s" % option)
