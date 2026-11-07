# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.microsoft_calendar.models.res_users import ResUsers
from odoo.addons.microsoft_calendar.tests.common import TestCommon, mock_get_token, patch_api
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService


@patch.object(ResUsers, '_get_microsoft_calendar_token', mock_get_token)
class TestResetAccount(TestCommon):

    @patch_api
    def setUp(self):
        super().setUp()
        self.create_events_for_tests()

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_reset_account_delete_from_odoo_sends_no_request(self, mock_delete):
        events = self.simple_event | self.recurrent_events
        wizard = self.env['microsoft.calendar.account.reset'].create({
            'user_id': self.organizer_user.id,
            'delete_policy': 'delete_odoo',
            'sync_policy': 'new',
        })
        with patch.object(self.env.cr, 'commit', lambda: None):
            wizard.reset_account()
        self.call_post_commit_hooks()

        self.assertFalse(events.exists())
        mock_delete.assert_not_called()

    @patch_api
    def test_reset_account_sync_all_reinserts_events(self):
        self.assertTrue(self.simple_event.microsoft_id)
        self.assertTrue(self.simple_event.ms_universal_event_id)

        wizard = self.env['microsoft.calendar.account.reset'].create({
            'user_id': self.organizer_user.id,
            'delete_policy': 'dont_delete',
            'sync_policy': 'all',
        })
        with patch.object(self.env.cr, 'commit', lambda: None):
            wizard.reset_account()

        self.simple_event.with_user(self.organizer_user)._sync_odoo2microsoft()

        self.assertFalse(self.simple_event.microsoft_id)
        self.assertFalse(self.simple_event.ms_universal_event_id)
        self.assertTrue(self.simple_event.need_sync_m)
        self.simple_event._microsoft_insert.assert_called_once()
        self.simple_event._microsoft_patch.assert_not_called()
