from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged

from odoo.addons.google_account.models.google_service import (
    GOOGLE_AUTH_ENDPOINT,
    GOOGLE_TOKEN_ENDPOINT,
    _get_client_secret,
)
from odoo.addons.mixin_encryption.tests.common import EncryptionKeyCase

MODULE = "odoo.addons.google_account.models.google_service"


@tagged("post_install", "-at_install")
class TestGoogleService(EncryptionKeyCase, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["google.service"]
        cls.icp = cls.env["ir.config_parameter"].sudo()

    def test_get_client_id_reads_config(self):
        """The client id is read from the service-specific config parameter."""
        self.icp.set_param("google_gmail_client_id", "CID-123")
        self.assertEqual(self.service._get_client_id("gmail"), "CID-123")

    def test_get_client_secret_reads_the_vault(self):
        """The client secret helper reads the service's secret out of the vault."""
        self.env["credential.credential"]._set_system_secret(
            "google_gmail_client_secret", "SECRET-xyz"
        )
        self.assertEqual(_get_client_secret(self.icp, "gmail"), "SECRET-xyz")
        self.assertFalse(self.icp.get_param("google_gmail_client_secret"))

    def test_authorize_uri_encodes_all_params(self):
        """The authorize URI embeds the endpoint and the encoded parameters."""
        self.icp.set_param("google_gmail_client_id", "CID-123")
        uri = self.service._get_authorize_uri(
            "gmail",
            scope="https://scope",
            redirect_uri="https://cb",
            state="STATE",
            access_type="offline",
        )
        self.assertTrue(uri.startswith(GOOGLE_AUTH_ENDPOINT + "?"))
        self.assertIn("response_type=code", uri)
        self.assertIn("client_id=CID-123", uri)
        self.assertIn("state=STATE", uri)
        self.assertIn("access_type=offline", uri)

    def test_do_request_rejects_unknown_method(self):
        """An unsupported HTTP method is rejected before any request is made."""
        with self.assertRaises(Exception):
            self.service._do_request("/drive/v3/files", method="FETCH")

    def test_do_request_post_returns_status_and_json(self):
        """A POST request returns the HTTP status and decoded JSON body."""
        res = MagicMock(status_code=200, headers={})
        res.json.return_value = {"access_token": "AT"}
        with patch.object(GuardedSession, "request", return_value=res) as req:
            status, response, _dummy = self.service._do_request(
                GOOGLE_TOKEN_ENDPOINT, params={"a": 1}, method="POST", preuri=""
            )
        self.assertEqual(status, 200)
        self.assertEqual(response, {"access_token": "AT"})
        self.assertEqual(req.call_args.args[0], "post")

    def test_get_google_tokens_unpacks_response(self):
        """Token exchange returns the access, refresh, and expiry values."""
        with patch(
            f"{MODULE}.GoogleService._do_request",
            return_value=(
                200,
                {"access_token": "AT", "refresh_token": "RT", "expires_in": 3600},
                False,
            ),
        ):
            tokens = self.service._get_google_tokens("code", "gmail", "https://cb")
        self.assertEqual(tokens, ("AT", "RT", 3600))

    def test_get_google_tokens_raises_on_http_error(self):
        """A failed token exchange surfaces a configuration warning."""
        with patch(
            f"{MODULE}.GoogleService._do_request", side_effect=requests.HTTPError()
        ):
            with self.assertRaises(UserError):
                self.service._get_google_tokens("bad-code", "gmail", "https://cb")

    def test_refresh_google_token_returns_access_and_expiry(self):
        """Refreshing a token returns the new access token and its expiry."""
        with patch(
            f"{MODULE}.GoogleService._do_request",
            return_value=(200, {"access_token": "AT2", "expires_in": 1800}, False),
        ):
            self.assertEqual(
                self.service._refresh_google_token("gmail", "rtoken"), ("AT2", 1800)
            )
