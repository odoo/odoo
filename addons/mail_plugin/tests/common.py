import functools
import json
from datetime import timedelta
from unittest.mock import patch

from odoo import SUPERUSER_ID, fields
from odoo.tests.common import HttpCase

from odoo.addons.mail.tests.common import mail_new_test_user

OUTLOOK_SCOPE = "odoo.plugin.outlook"


def outlook_api_key(env, login):
    user = env["res.users"].with_user(SUPERUSER_ID).search([("login", "=", login)])
    return (
        env["res.users.apikeys"]
        .with_user(user)
        ._generate(
            OUTLOOK_SCOPE,
            f"mail plugin test ({login})",
            fields.Datetime.now() + timedelta(days=1),
        )
    )


def as_outlook_user(login):
    """Run the test with a real Outlook-scoped API key in the Authorization
    header, so the route's `auth="bearer", scope=...` is what admits it."""

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            key = outlook_api_key(self.env, login)
            self.opener.headers["Authorization"] = f"Bearer {key}"
            try:
                return method(self, *args, **kwargs)
            finally:
                self.opener.headers.pop("Authorization", None)

        return wrapper

    return decorator


class TestMailPluginControllerCommon(HttpCase):
    def setUp(self):
        super().setUp()
        self.user_test = mail_new_test_user(
            self.env,
            login="employee",
            groups="base.group_user,base.group_partner_manager",
        )

    @as_outlook_user("employee")
    def mock_plugin_partner_get(self, name, email, patched_iap_enrich):
        data = {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"email": email, "name": name},
        }

        with patch(
            "odoo.addons.mail_plugin.controllers.mail_plugin.MailPluginController"
            "._iap_enrich",
            new=patched_iap_enrich,
        ):
            result = self.url_open(
                "/mail_plugin/partner/get",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
            )

        if not result.ok:
            return {}

        return result.json().get("result", {})

    @as_outlook_user("employee")
    def mock_enrich_and_create_company(self, partner_id, patched_iap_enrich):
        data = {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"partner_id": partner_id},
        }

        with patch(
            "odoo.addons.mail_plugin.controllers.mail_plugin.MailPluginController"
            "._iap_enrich",
            new=patched_iap_enrich,
        ):
            result = self.url_open(
                "/mail_plugin/partner/enrich_and_create_company",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
            )

        if not result.ok:
            return {}

        return result.json().get("result", {})
