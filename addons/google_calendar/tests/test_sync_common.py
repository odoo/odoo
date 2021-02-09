# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_calendar.models.res_users import User
from odoo.addons.google_calendar.models.google_sync import GoogleSync

def patch_api(func):
    @patch.object(GoogleSync, '_google_insert', MagicMock(spec=GoogleSync._google_insert))
    @patch.object(GoogleSync, '_google_delete', MagicMock(spec=GoogleSync._google_delete))
    @patch.object(GoogleSync, '_google_patch', MagicMock(spec=GoogleSync._google_patch))
    def patched(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return patched

@patch.object(User, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncGoogle(TransactionCase):

    def setUp(self):
        super().setUp()
        self.google_service = GoogleCalendarService(self.env['google.service'])

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
