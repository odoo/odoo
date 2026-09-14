from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests

from odoo import fields
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged

from odoo.addons.mixin_encryption.tests.common import EncryptionKeyCase

TOKEN_URL = "https://oauth.example.com/token"


@tagged("post_install", "-at_install")
class TestOAuth2Refresh(EncryptionKeyCase, TransactionCase):
    def _credential(self, **vals):
        return self.env["credential.credential"].create(
            {
                "name": "OAuth probe",
                "category_id": self.env.ref("credential.credential_category_oauth2").id,
                "oauth_access_token": "old-access",
                "oauth_refresh_token": "the-refresh",
                **vals,
            }
        )

    def _response(self, ok=True, payload=None, status=200):
        response = MagicMock(ok=ok, status_code=status)
        response.json.return_value = payload or {}
        return response

    def _refresh(self, credential, response):
        with patch.object(GuardedSession, "request", return_value=response) as sent:
            result = credential._oauth2_refresh(
                TOKEN_URL, "client", "secret", purpose="probe", extra={"scope": "s"}
            )
        return result, sent

    def test_the_refresh_grant_stores_the_new_token_and_its_expiry(self):
        credential = self._credential()
        (access, seconds), sent = self._refresh(
            credential,
            self._response(payload={"access_token": "new-access", "expires_in": 3600}),
        )

        self.assertEqual((access, seconds), ("new-access", 3600))
        data = sent.call_args.kwargs["data"]
        self.assertEqual(data["grant_type"], "refresh_token")
        self.assertEqual(data["refresh_token"], "the-refresh")
        self.assertEqual((data["client_id"], data["scope"]), ("client", "s"))
        self.assertEqual(credential.oauth_access_token, "new-access")
        self.assertEqual(credential.oauth_refresh_token, "the-refresh")
        self.assertGreater(
            credential.oauth_token_date_expiration,
            fields.Datetime.now() + timedelta(minutes=59),
        )

    def test_a_rotated_refresh_token_replaces_the_spent_one(self):
        credential = self._credential()
        self._refresh(
            credential,
            self._response(
                payload={
                    "access_token": "new-access",
                    "refresh_token": "next-refresh",
                    "expires_in": 60,
                }
            ),
        )

        self.assertEqual(credential.oauth_refresh_token, "next-refresh")

    def test_a_token_refreshed_while_waiting_for_the_lock_is_taken_as_is(self):
        credential = self._credential(
            oauth_token_date_expiration=fields.Datetime.now() + timedelta(hours=1)
        )
        (access, seconds), sent = self._refresh(credential, self._response())

        sent.assert_not_called()
        self.assertEqual(access, "old-access")
        self.assertGreater(seconds, 3500)

    def test_a_refused_grant_raises_with_the_response(self):
        credential = self._credential()
        refused = self._response(ok=False, status=400)
        with self.assertRaises(requests.HTTPError) as caught:
            self._refresh(credential, refused)

        self.assertIs(caught.exception.response, refused)
        self.assertEqual(credential.oauth_access_token, "old-access")
