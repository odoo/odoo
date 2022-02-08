# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.models.res_users import User
from odoo.addons.microsoft_calendar.models.microsoft_sync import MicrosoftSync
from odoo.modules.registry import Registry
from odoo.addons.microsoft_account.models.microsoft_service import TIMEOUT


def patch_api(func):
    @patch.object(MicrosoftSync, '_microsoft_insert', MagicMock())
    @patch.object(MicrosoftSync, '_microsoft_delete', MagicMock())
    @patch.object(MicrosoftSync, '_microsoft_patch', MagicMock())
    def patched(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return patched

@patch.object(User, '_get_microsoft_calendar_token', lambda user: 'dummy-token')
class TestSyncOdoo2Microsoft(TransactionCase):

    def setUp(self):
        super().setUp()
        self.microsoft_service = MicrosoftCalendarService(self.env['microsoft.service'])

    def assertMicrosoftEventInserted(self, values):
        MicrosoftSync._microsoft_insert.assert_called_once_with(self.microsoft_service, values)

    def assertMicrosoftEventNotInserted(self):
        MicrosoftSync._microsoft_insert.assert_not_called()

    def assertMicrosoftEventPatched(self, microsoft_id, values, timeout=None):
        expected_args = (microsoft_id, values)
        expected_kwargs = {'timeout': timeout} if timeout else {}
        MicrosoftSync._microsoft_patch.assert_called_once()
        args, kwargs = MicrosoftSync._microsoft_patch.call_args
        self.assertEqual(args[1:], expected_args) # skip Google service arg
        self.assertEqual(kwargs, expected_kwargs)

    @patch_api
    def test_stop_synchronization(self):
        self.env.user.stop_microsoft_synchronization()
        self.assertTrue(self.env.user.microsoft_synchronization_stopped, "The microsoft synchronization flag should be switched on")
        self.assertFalse(self.env.user._sync_microsoft_calendar(self.microsoft_service), "The microsoft synchronization should be stopped")
        year = date.today().year - 1

        # If synchronization stopped, creating a new event should not call _google_insert.
        self.env['calendar.event'].create({
            'name': "Event",
            'start': datetime(year, 1, 15, 8, 0),
            'stop': datetime(year, 1, 15, 18, 0),
            'privacy': 'private',
        })
        self.assertMicrosoftEventNotInserted()

    @patch_api
    def test_restart_synchronization(self):
        # Test new event created after stopping synchronization are correctly patched when restarting sync.
        self.maxDiff = None
        microsoft_id = 'aaaaaaaaa'
        year = date.today().year
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        user = self.env['res.users'].create({
            'name': 'Test user Calendar',
            'login': 'jean-luc@opoo.com',
            'partner_id': partner.id,
        })
        user.stop_microsoft_synchronization()
        # In case of full sync, limit to a range of 1y in past and 1y in the future by default
        event = self.env['calendar.event'].with_user(user).create({
            'microsoft_id': microsoft_id,
            'name': "Event",
            'start': datetime(year, 1, 15, 8, 0),
            'stop': datetime(year, 1, 15, 18, 0),
            'partner_ids': [(4, partner.id)],
        })

        user.with_user(user).restart_microsoft_synchronization()
        event.with_user(user)._sync_odoo2microsoft(self.microsoft_service)
        microsoft_guid = self.env['ir.config_parameter'].sudo().get_param('microsoft_calendar.microsoft_guid', False)
        self.assertMicrosoftEventPatched(event.microsoft_id, {
            'id': event.microsoft_id,
            'start': {'dateTime': '%s-01-15T08:00:00+00:00' % year, 'timeZone': 'Europe/London'},
            'end': {'dateTime': '%s-01-15T18:00:00+00:00' % year, 'timeZone': 'Europe/London'},
            'subject': 'Event',
            'body': {'content': '', 'contentType': 'text'},
            'attendees': [],
            'isAllDay': False,
            'isOrganizer': True,
            'isReminderOn': False,
            'sensitivity': 'normal',
            'showAs': 'busy',
            'location': {'displayName': ''},
            'organizer': {'emailAddress': {'address': 'jean-luc@opoo.com', 'name': 'Test user Calendar'}},
            'reminderMinutesBeforeStart': 0,
            'singleValueExtendedProperties': [{
                    'id': 'String {%s} Name odoo_id' % microsoft_guid,
                    'value': str(event.id),
                }, {
                    'id': 'String {%s} Name owner_odoo_id' % microsoft_guid,
                    'value': str(user.id),
                }
            ]
        })
