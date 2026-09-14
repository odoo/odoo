from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests

from odoo import fields
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged


TOKEN_URL = "https://oauth.example.com/token"


@tagged("post_install", "-at_install")
class TestOAuth2Refresh(TransactionCase):
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

    def test_the_row_is_locked_before_the_refresh_token_is_read(self):
        credential = self._credential()
        Credential = type(credential)
        events = []
        lock = Credential.lock_for_update
        payload = Credential._use_secret_payload

        def locking(records, **kwargs):
            events.append("lock")
            return lock(records, **kwargs)

        def reading(records, purpose):
            events.append("read")
            return payload(records, purpose)

        with (
            patch.object(Credential, "lock_for_update", locking),
            patch.object(Credential, "_use_secret_payload", reading),
        ):
            self._refresh(
                credential,
                self._response(payload={"access_token": "new", "expires_in": 60}),
            )

        self.assertEqual(events[:2], ["lock", "read"])


@tagged("post_install", "-at_install")
class TestHeldOAuth2RefreshGrant(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company._set_held_secrets({"probe_refresh_token": "held-refresh"})

    def _grant(self, response=None, **kwargs):
        response = response or MagicMock(ok=True, status_code=200)
        with patch.object(GuardedSession, "request", return_value=response) as sent:
            result = self.company._post_held_oauth2_refresh_grant(
                TOKEN_URL,
                kwargs.pop("refresh_key", "probe_refresh_token"),
                {"client_assertion": "signed-jwt"},
                purpose="probe",
                **kwargs,
            )
        return result, sent

    def test_the_held_refresh_token_is_spent_with_the_client_auth(self):
        response = MagicMock(ok=True, status_code=200)
        result, sent = self._grant(response, headers={"accept": "application/json"})

        self.assertIs(result, response)
        self.assertEqual(
            sent.call_args.kwargs["data"],
            {
                "grant_type": "refresh_token",
                "refresh_token": "held-refresh",
                "client_assertion": "signed-jwt",
            },
        )
        self.assertEqual(sent.call_args.kwargs["headers"]["accept"], "application/json")

    def test_nothing_is_sent_without_a_held_refresh_token(self):
        result, sent = self._grant(refresh_key="probe_missing_token")

        self.assertIsNone(result)
        sent.assert_not_called()
