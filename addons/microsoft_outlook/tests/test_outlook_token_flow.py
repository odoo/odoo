"""Tests for the Outlook OAuth token flows, with the HTTP layer mocked."""

import time
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged


# the flow itself lives in the shared provider mixin
MIXIN_MODULE = "odoo.addons.mail_oauth2.models.mixin_oauth2_mail_provider"


@tagged("post_install", "-at_install")
class TestOutlookTokenFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mixin = cls.env["mixin.microsoft.outlook"]
        cls.env["ir.config_parameter"].sudo().set_param(
            "microsoft_outlook_client_id", "test-client-id"
        )
        cls.env["credential.credential"]._set_system_secret(
            "microsoft_outlook_client_secret", "test-client-secret"
        )

    def _response(self, ok=True, payload=None):
        response = MagicMock()
        response.ok = ok
        response.json.return_value = payload or {}
        response.text = "mock"
        return response

    def test_fetch_token_returns_payload(self):
        """A successful token request returns the endpoint's JSON payload."""
        payload = {"access_token": "AT", "expires_in": 3600}
        with patch.object(
            GuardedSession,
            "request",
            return_value=self._response(payload=payload),
        ) as post:
            result = self.Mixin._get_outlook_token("refresh_token", refresh_token="RT")
        self.assertEqual(result, payload)
        sent = post.call_args.kwargs["data"]
        self.assertEqual(sent["client_id"], "test-client-id")
        self.assertEqual(sent["grant_type"], "refresh_token")

    def test_fetch_token_http_error_rejected(self):
        """A non-2xx token response surfaces as a UserError (negative)."""
        with (
            patch.object(
                GuardedSession, "request", return_value=self._response(ok=False)
            ),
            self.assertRaises(UserError),
        ):
            self.Mixin._get_outlook_token("refresh_token", refresh_token="RT")

    def test_refresh_token_maps_tuple_and_expiration(self):
        """The authorization-code exchange maps to (refresh, access, expiry)."""
        payload = {"refresh_token": "RT", "access_token": "AT", "expires_in": 1000}
        before = int(time.time())
        with patch.object(
            GuardedSession,
            "request",
            return_value=self._response(payload=payload),
        ):
            refresh, access, expiration = self.Mixin._get_outlook_refresh_token("CODE")
        self.assertEqual((refresh, access), ("RT", "AT"))
        self.assertGreaterEqual(expiration, before + 1000)

    def test_renewing_stores_the_rotated_refresh_token(self):
        """Microsoft rotates the refresh token: renewal keeps the new one on the credential."""
        server = self.env["ir.mail_server"].create(
            {"name": "Outlook probe", "smtp_host": "smtp.office365.com"}
        )
        server._oauth2_store_tokens(access_token="AT1", refresh_token="RT")
        payload = {
            "refresh_token": "RT2",
            "access_token": "AT2",
            "id_token": "IDT",
            "expires_in": 500,
        }
        with patch.object(
            GuardedSession,
            "request",
            return_value=self._response(payload=payload),
        ) as post:
            server._renew_outlook_access_token()
        post.assert_called_once()
        self.assertEqual(
            (
                server.microsoft_outlook_refresh_token,
                server.microsoft_outlook_access_token,
            ),
            ("RT2", "AT2"),
        )

    def test_iap_http_error_rejected(self):
        """An IAP transport failure surfaces as a UserError (negative)."""
        with (
            patch.object(
                GuardedSession, "request", return_value=self._response(ok=False)
            ),
            self.assertRaises(UserError),
        ):
            self.Mixin._get_outlook_access_token_iap("RT")

    def test_iap_payload_error_rejected(self):
        """An IAP error payload is converted into a UserError (negative)."""
        with (
            patch.object(
                GuardedSession,
                "request",
                return_value=self._response(payload={"error": "no_subscription"}),
            ),
            self.assertRaises(UserError),
        ):
            self.Mixin._get_outlook_access_token_iap("RT")
