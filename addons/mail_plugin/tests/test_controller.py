# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import Mock, patch

from odoo.addons.mail_plugin.tests.common import TestMailPluginControllerCommon
from odoo.tests import mute_logger
from odoo.exceptions import AccessError


class TestMailPluginController(TestMailPluginControllerCommon):
    @mute_logger('odoo.http')
    def test_get_partner_no_access(self):
        """Test the case where the partner has been enriched by someone else, but we can't access it."""
        partner = self.env["res.partner"].create({"name": "Test", "email": "test@test.example.com"})
        partner_count = self.env['res.partner'].search_count([])
        # sanity check, we can access the partner
        result = self.mock_plugin_partner_get(
            "Test", "test@test.example.com",
            lambda _, domain: {"name": "Name", "email": "test@test.example.com"},
        )
        self.assertEqual(result["partner"]["name"], "Test")
        new_partner_count = self.env['res.partner'].search_count([])
        self.assertEqual(new_partner_count, partner_count, "Should not have created a new partner")

        # now we can't access it
        def _check_access(record, operation):
            if operation == "read" and record == partner:
                return record, lambda: AccessError("No Access")
            return None

        with patch.object(type(partner), '_check_access', _check_access):
            result = self.mock_plugin_partner_get(
                "Test", "test@test.example.com",
                lambda _, domain: {"name": "Name", "email": "test@test.example.com"},
            )

        self.assertFalse(result.get("partner"))

    def test_get_partner_is_default_from(self):
        """When the email_from is the server default from address, we return a custom message instead of trying to match a partner record."""
        self.env['mail.alias.domain'].create({'name': 'example.com', 'default_from': 'notification'})
        mock_iap_enrich = Mock()
        result = self.mock_plugin_partner_get("Test partner", "notificaTION@EXAMPLE.COM", mock_iap_enrich)
        self.assertEqual(
            result,
            {
                'partner': {},
                'error': 'This is your notification address. Search the Contact manually to link this email to a record.',
            },
        )
