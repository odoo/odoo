# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_account.models.google_service import GoogleService
from odoo.addons.google_calendar.models.res_users import User
from odoo.addons.google_calendar.models.google_sync import google_calendar_token, GoogleSync
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import HttpCase


def patch_api(func):
    def patched(self, *args, **kwargs):
        with self.mock_google_sync():
            return func(self, *args, **kwargs)
    return patched

@patch.object(User, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncGoogle(HttpCase):

    def setUp(self):
        super().setUp()
        self.google_service = GoogleCalendarService(self.env['google.service'])
        self.env.user.sudo().unpause_google_synchronization()
        self.organizer_user = mail_new_test_user(self.env, login="organizer_user")
        self.attendee_user = mail_new_test_user(self.env, login='attendee_user')

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

        # as these are normally post-commit hooks, we don't change any state here
        def _mock_delete(model, service, google_id, **kwargs):
            with google_calendar_token(user_id or model.env.user.sudo()) as token:
                if token:
                    self._gsync_deleted_ids.append(google_id)

        def _mock_insert(model, service, values, **kwargs):
            if not values:
                return
            with google_calendar_token(user_id or model.env.user.sudo()) as token:
                if token:
                    self._gsync_insert_values.append((values, kwargs))

        def _mock_patch(model, service, google_id, values, **kwargs):
            with google_calendar_token(user_id or model.env.user.sudo()) as token:
                if token:
                    self._gsync_patch_values[google_id].append((values, kwargs))

        with self.env.cr.savepoint(), \
             patch.object(GoogleSync, '_google_insert', autospec=True, wraps=GoogleSync, side_effect=_mock_insert), \
             patch.object(GoogleSync, '_google_delete', autospec=True, wraps=GoogleSync, side_effect=_mock_delete), \
             patch.object(GoogleSync, '_google_patch', autospec=True, wraps=GoogleSync, side_effect=_mock_patch):
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
        self.assertDictEqual(insert_kwargs, {'timeout': timeout} if timeout else {})

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

    def assertGoogleAPINotCalled(self):
        self.assertGoogleEventNotPatched()
        self.assertGoogleEventNotInserted()
        self.assertGoogleEventNotDeleted()

    def assertGoogleEventSendUpdates(self, expected_value):
        self.assertEqual(len(self._gservice_request_uris), 1)
        uri = self._gservice_request_uris[0]
        uri_parameter = "sendUpdates=%s" % expected_value
        self.assertIn(uri_parameter, uri, "The URL should contain %s" % uri_parameter)

    def call_post_commit_hooks(self):
        """
        manually calls postcommit hooks defined with the decorator @after_commit
        """

        funcs = self.env.cr.postcommit._funcs.copy()
        while funcs:
            func = funcs.popleft()
            func()
