"""Tests for the Gmail OAuth token flows, with the HTTP layer mocked."""

import time
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged


# the flow itself lives in the shared provider mixin
MIXIN_MODULE = "odoo.addons.mail_oauth2.models.mixin_oauth2_mail_provider"


@tagged("post_install", "-at_install")
class TestGmailTokenFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mixin = cls.env["mixin.google.gmail"]
        cls.env["ir.config_parameter"].sudo().set_param(
            "google_gmail_client_id", "test-client-id"
        )
        cls.env["credential.credential"]._set_system_secret(
            "google_gmail_client_secret", "test-client-secret"
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
            result = self.Mixin._get_gmail_token("refresh_token", refresh_token="RT")
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
            self.Mixin._get_gmail_token("refresh_token", refresh_token="RT")

    def test_refresh_token_maps_tuple_and_expiration(self):
        """The authorization-code exchange maps to (refresh, access, expiry)."""
        payload = {"refresh_token": "RT", "access_token": "AT", "expires_in": 1000}
        before = int(time.time())
        with patch.object(
            GuardedSession,
            "request",
            return_value=self._response(payload=payload),
        ):
            refresh, access, expiration = self.Mixin._get_gmail_refresh_token("CODE")
        self.assertEqual((refresh, access), ("RT", "AT"))
        self.assertGreaterEqual(expiration, before + 1000)

    def test_renewing_runs_the_refresh_grant_on_the_servers_credential(self):
        """With client credentials set, renewal refreshes through the server's credential."""
        server = self.env["ir.mail_server"].create(
            {"name": "Gmail probe", "smtp_host": "smtp.gmail.com"}
        )
        server._oauth2_store_tokens(access_token="AT1", refresh_token="RT")
        payload = {"access_token": "AT2", "expires_in": 500}
        before = int(time.time())
        with patch.object(
            GuardedSession,
            "request",
            return_value=self._response(payload=payload),
        ) as post:
            server._renew_gmail_access_token()
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["data"]["refresh_token"], "RT")
        self.assertEqual(server.google_gmail_access_token, "AT2")
        self.assertEqual(server.google_gmail_refresh_token, "RT")
        self.assertGreaterEqual(
            server.google_gmail_access_token_expiration, before + 500
        )

    def test_a_refused_refresh_is_a_user_error(self):
        """A refused refresh grant surfaces as a UserError (negative)."""
        server = self.env["ir.mail_server"].create(
            {"name": "Gmail probe", "smtp_host": "smtp.gmail.com"}
        )
        server._oauth2_store_tokens(access_token="AT1", refresh_token="RT")
        with (
            patch.object(
                GuardedSession, "request", return_value=self._response(ok=False)
            ),
            self.assertRaises(UserError),
        ):
            server._renew_gmail_access_token()

    def test_iap_http_error_rejected(self):
        """An IAP transport failure surfaces as a UserError (negative)."""
        with (
            patch.object(
                GuardedSession, "request", return_value=self._response(ok=False)
            ),
            self.assertRaises(UserError),
        ):
            self.Mixin._get_gmail_access_token_iap("RT")

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
            self.Mixin._get_gmail_access_token_iap("RT")
