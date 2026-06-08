# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from contextlib import contextmanager
from unittest.mock import patch

from odoo import SUPERUSER_ID
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.http import request
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@contextmanager
def mock_auth_method_outlook(login):
    """Mock the Outlook auth method.

    This must be used as a method decorator.

    :param login: Login of the user used for the authentication
    """

    def patched_auth_method_outlook(*args, **kwargs):
        request.update_env(
            user=request.env["res.users"]
            .with_user(SUPERUSER_ID)
            .search([("login", "=", login)], limit=1)
        )

    with patch(
        "odoo.addons.mail_plugin.models.ir_http.IrHttp._auth_method_outlook",
        new=patched_auth_method_outlook,
    ):
        yield


@tagged("at_install", "-post_install")  # LEGACY at_install
class TestMailPluginController(HttpCase):
    def setUp(self):
        super().setUp()
        self.user_test = mail_new_test_user(
            self.env,
            login="employee",
            groups="base.group_user,base.group_partner_manager",
        )

    @mock_auth_method_outlook("employee")
    def make_request(self, url, params):
        """Make a request while patching the authentication process."""
        data = {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
        }

        result = self.url_open(
            url,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )

        if not result.ok:
            return {}

        return result.json().get("result", {})

    def test_get_partner_is_default_from(self):
        """When the email_from is the server default from address, we return a custom message instead of trying to match a partner record."""
        self.env["mail.alias.domain"].create(
            {"name": "example.com", "default_from": "notification"}
        )
        data = {
            "email": "notificaTION@EXAMPLE.COM",
            "name": "Test partner",
        }
        result = self.make_request("/mail_plugin/partner/get", data)
        self.assertFalse(result.get('partner'))

        result = self.make_request("/mail_plugin/partner/create", data)
        self.assertFalse(result)

        data = {
            "email": "other@EXAMPLE.COM",
            "name": "Test partner",
        }
        result = self.make_request("/mail_plugin/partner/create", data)
        self.assertEqual(result.get('name'), 'Test partner')
        self.assertEqual(result.get('email'), 'other@EXAMPLE.COM')
