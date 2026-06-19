# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo import Command
from odoo.addons.google_calendar.models.calendar_calendar import CalendarCalendar
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService
from odoo.addons.google_account.models.google_service import GoogleService
from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.models.google_event_sync import GoogleEventSync
from odoo.addons.google_calendar.models.google_sync import google_calendar_token
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import HttpCase

from odoo.tools import mute_logger


def patch_api(func):
    def patched(self, *args, **kwargs):
        with self.mock_google_sync():
            return func(self, *args, **kwargs)
    return patched


@patch.object(ResUsers, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncGoogle(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.google_service = GoogleCalendarService(cls.env['google.service'])
        cls.env.user.sudo().unpause_google_synchronization()
        cls.organizer_user = mail_new_test_user(cls.env, login="organizer_user")
        cls.organizer_user.primary_calendar.google_id = "organizer-primary"
        cls.attendee_user = mail_new_test_user(cls.env, login='attendee_user')
        cls.attendee_user.primary_calendar.google_id = "attendee-primary"

        cls.secondary_calendar = cls.env['calendar.calendar'].with_user(cls.organizer_user).create({
            'name': "Secondary Calendar",
            'google_id': "Secondary",
        })

        m = mute_logger('odoo.addons.auth_signup.models.res_users')
        mute_logger.__enter__(m)  # noqa: PLC2801
        cls.addClassCleanup(mute_logger.__exit__, m, None, None, None)

    @contextmanager
    def mock_datetime_and_now(self, mock_dt):
        """
        Used when synchronization date (using env.cr.now()) is important
        in addition to standard datetime mocks. Used mainly to detect sync
        issues.
        """
        with freeze_time(mock_dt), \
                patch.object(self.env.cr, 'now', lambda: mock_dt):
            yield

    @contextmanager
    def mock_google_sync(self, user_id=None):
        self._gsync_deleted_ids = []
        self._gsync_insert_values = []
        self._gsync_patch_values = defaultdict(list)
        self._gsync_moved_ids = []
        self._gsync_deleted_calendar_ids = []
        self._gsync_inserted_calendar_values = []
        self._gsync_patched_calendar_values = defaultdict(list)

        # as these are normally post-commit hooks, we don't change any state here
        def _mock_delete(model, service, calendar, google_id, **kwargs):
            if self.env.user._get_google_sync_status() != "sync_active" or not calendar:
                return
            with google_calendar_token(user_id or model.env.user.sudo()) as token:
                if token:
                    self._gsync_deleted_ids.append(google_id)

        def _mock_insert(model, service, calendar, values, **kwargs):
            if not values or self.env.user._get_google_sync_status() != "sync_active" or not calendar:
                return
            with google_calendar_token(user_id or model.env.user.sudo()) as token:
                if token:
                    self._gsync_insert_values.append((values, kwargs))
                    model.write({
                        'google_id': f'event-{model.id}',
                    })

        def _mock_patch(model, service, calendar, google_id, values, **kwargs):
            if self.env.user._get_google_sync_status() != "sync_active" or not calendar:
                return
            with google_calendar_token(user_id or model.env.user.sudo()) as token:
                if token:
                    self._gsync_patch_values[google_id].append((values, kwargs))

        def _mock_move(model, service, source_calendar, destination_calendar, **kwargs):
            if self.env.user._get_google_sync_status() != "sync_active" or not source_calendar or not destination_calendar:
                return
            with (google_calendar_token(user_id or model.env.user.sudo()) as token):
                if token:
                    model.last_google_calendar_sync_id = destination_calendar
                    self._gsync_moved_ids.append((model.google_id, source_calendar, destination_calendar))

        def _mock_insert_calendar(model, service, **kwargs):
            with google_calendar_token(user_id or model.env.user.sudo()) as token:
                if token:
                    self._gsync_inserted_calendar_values.append(model._google_values())

        def _mock_patch_calendar(model, service, **kwargs):
            with google_calendar_token(user_id or model.env.user.sudo()) as token:
                if token:
                    self._gsync_patched_calendar_values[model.id].append((model._google_values(), kwargs))

        with self.env.cr.savepoint(), \
             patch.object(GoogleEventSync, '_google_insert', autospec=True, wraps=GoogleEventSync, side_effect=_mock_insert), \
             patch.object(GoogleEventSync, '_google_delete', autospec=True, wraps=GoogleEventSync, side_effect=_mock_delete), \
             patch.object(GoogleEventSync, '_google_patch', autospec=True, wraps=GoogleEventSync, side_effect=_mock_patch), \
             patch.object(GoogleEventSync, '_google_move', autospec=True, wraps=GoogleEventSync, side_effect=_mock_move), \
             patch.object(CalendarCalendar, '_google_calendar_insert', autospec=True, side_effect=_mock_insert_calendar), \
             patch.object(CalendarCalendar, '_google_calendar_patch', autospec=True, side_effect=_mock_patch_calendar):
            yield

    @contextmanager
    def mock_google_service(self):
        self._gservice_request_uris = []

        def _mock_do_request(model, uri, *args, **kwargs):
            self._gservice_request_uris.append(uri)
            return (200, {}, datetime.now())

        with patch.object(GoogleService, '_do_request', autospec=True, wraps=GoogleService, side_effect=_mock_do_request):
            yield

    def assertGoogleEventDeleted(self, google_id):
        self.assertIn(google_id, self._gsync_deleted_ids, "Event should have been deleted")

    def assertGoogleEventNotDeleted(self):
        self.assertFalse(self._gsync_deleted_ids)

    def assertGoogleEventInserted(self, values, timeout=None):
        self.assertEqual(len(self._gsync_insert_values), 1)
        matching = []
        for insert_values, insert_kwargs in self._gsync_insert_values:
            if all(insert_values.get(key, False) == value for key, value in values.items()):
                matching.append((insert_values, insert_kwargs))
        self.assertGreaterEqual(len(matching), 1, 'There must be at least 1 matching insert.')
        insert_values, insert_kwargs = matching[0]
        if timeout is not None:
            self.assertDictEqual(insert_kwargs, {'timeout': timeout})

    def assertGoogleEventInsertedMultiTime(self, values, timeout=None):
        self.assertGreaterEqual(len(self._gsync_insert_values), 1)
        matching = []
        for insert_values, insert_kwargs in self._gsync_insert_values:
            if all(insert_values.get(key, False) == value for key, value in values.items()):
                matching.append((insert_values, insert_kwargs))
        self.assertGreaterEqual(len(matching), 1, 'There must be at least 1 matching insert.')
        insert_values, insert_kwargs = matching[0]
        self.assertDictEqual(insert_kwargs, {'timeout': timeout} if timeout else {})

    def assertGoogleEventNotInserted(self):
        self.assertFalse(self._gsync_insert_values)

    def assertGoogleEventPatched(self, google_id, values, timeout=None):
        patch_values_all = self._gsync_patch_values.get(google_id)
        self.assertTrue(patch_values_all)
        matching = []
        for patch_values, patch_kwargs in patch_values_all:
            if all(patch_values.get(key, False) == values[key] for key in values):
                matching.append((patch_values, patch_kwargs))
        self.assertGreaterEqual(len(matching), 1, 'There must be at least 1 matching patch.')
        patch_values, patch_kwargs = matching[0]
        self.assertDictEqual(patch_kwargs, {'timeout': timeout} if timeout else {})

    def assertGoogleEventNotPatched(self):
        self.assertFalse(self._gsync_patch_values)

    def assertGoogleEventMoved(self, google_id, source_calendar_id, destination_calendar_id):
        self.assertIn((google_id, source_calendar_id, destination_calendar_id), self._gsync_moved_ids,
                      "Event should have been moved from %s to %s" % (source_calendar_id, destination_calendar_id))

    def assertGoogleEventNotMoved(self):
        self.assertFalse(self._gsync_moved_ids)

    def assertGoogleCalendarInserted(self, values):
        self.assertEqual(len(self._gsync_inserted_calendar_values), 1)
        matching = []
        for insert_values in self._gsync_inserted_calendar_values:
            if all(insert_values.get(key, False) == value for key, value in values.items()):
                matching.append(insert_values)
        self.assertGreaterEqual(len(matching), 1, 'There must be at least 1 matching insert.')

    def assertGoogleCalendarNotInserted(self):
        self.assertFalse(self._gsync_inserted_calendar_values)

    def assertGoogleCalendarPatched(self, google_id, values):
        patch_values_all = self._gsync_patched_calendar_values.get(google_id)
        self.assertTrue(patch_values_all)
        matching = []
        for patch_values, patch_kwargs in patch_values_all:
            if all(patch_values.get(key, False) == values[key] for key in values):
                matching.append((patch_values, patch_kwargs))
        self.assertGreaterEqual(len(matching), 1, 'There must be at least 1 matching patch.')

    def assertGoogleCalendarNotPatched(self):
        self.assertFalse(self._gsync_patched_calendar_values)

    def assertGoogleAPINotCalled(self):
        self.assertGoogleEventNotPatched()
        self.assertGoogleEventNotInserted()
        self.assertGoogleEventNotDeleted()
        self.assertGoogleCalendarNotPatched()
        self.assertGoogleCalendarNotInserted()

    def assertGoogleEventSendUpdates(self, expected_value):
        self.assertEqual(len(self._gservice_request_uris), 1)
        uri = self._gservice_request_uris[0]
        uri_parameter = "sendUpdates=%s" % expected_value
        self.assertIn(uri_parameter, uri, "The URL should contain %s" % uri_parameter)

    def call_post_commit_hooks(self):
        """
        manually calls postcommit hooks defined with the decorator @after_commit
        """
        self.env.cr.flush()  # flush changes first
        funcs = self.env.cr.postcommit._funcs.copy()
        while funcs:
            func = funcs.popleft()
            func()

    def create_calendar(self, name='Test Calendar', user=False, google_id=False, is_primary=False, need_sync=True, active=True):
        calendar_user = user or self.organizer_user
        return self.env['calendar.calendar'].with_user(calendar_user).create({
            'name': name,
            'google_id': google_id or False,
            'need_sync': need_sync,
            'active': active,
            'calendar_users': [Command.create({
                'user_id': calendar_user.id,
                'access_role': 'owner',
                'is_primary': is_primary,
            })]
        })
