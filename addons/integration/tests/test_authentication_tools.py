import hashlib
import hmac
import time
from datetime import UTC, datetime
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.integration.tools.authentication import (
    _execute_custom_verification,
    execute_signature_verification,
    is_bearer_token_valid,
    is_hmac_signature_valid,
    is_timestamp_valid,
)


@tagged("post_install", "-at_install")
class TestAuthenticationTools(TransactionCase):
    @staticmethod
    def _hex(secret, body, hash_func=hashlib.sha256):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        return hmac.new(secret.encode("utf-8"), raw, hash_func).hexdigest()

    def test_bearer_valid(self):
        self.assertTrue(
            is_bearer_token_valid({"Authorization": "Bearer tok-123"}, "tok-123")
        )

    def test_bearer_rejects_mismatch(self):
        self.assertFalse(
            is_bearer_token_valid({"Authorization": "Bearer wrong"}, "tok-123")
        )

    def test_bearer_rejects_non_dict_headers(self):
        self.assertFalse(is_bearer_token_valid("not-a-dict", "tok"))

    def test_bearer_rejects_missing_prefix(self):
        self.assertFalse(is_bearer_token_valid({"Authorization": "Basic x"}, "tok"))

    def test_bearer_rejects_empty_token_and_expected(self):
        self.assertFalse(is_bearer_token_valid({"Authorization": "Bearer   "}, "tok"))
        self.assertFalse(is_bearer_token_valid({"Authorization": "Bearer tok"}, ""))

    def test_hmac_valid_str_body(self):
        body = '{"event":"ping"}'
        headers = {"X-Hub-Signature-256": "sha256=" + self._hex("shh", body)}
        self.assertTrue(is_hmac_signature_valid(headers, body, "shh", hashlib.sha256))

    def test_hmac_valid_bytes_body(self):
        body = b'{"event":"ping"}'
        headers = {"X-Hub-Signature-256": "sha256=" + self._hex("shh", body)}
        self.assertTrue(is_hmac_signature_valid(headers, body, "shh", hashlib.sha256))

    def test_hmac_rejects_wrong_secret(self):
        body = "payload"
        headers = {"X-Hub-Signature-256": "sha256=" + self._hex("shh", body)}
        self.assertFalse(
            is_hmac_signature_valid(headers, body, "other", hashlib.sha256)
        )

    def test_hmac_rejects_bad_inputs(self):
        self.assertFalse(is_hmac_signature_valid("x", "b", "s", hashlib.sha256))
        self.assertFalse(is_hmac_signature_valid({}, "b", "s", hashlib.sha256))
        self.assertFalse(
            is_hmac_signature_valid(
                {"X-Hub-Signature-256": "sha256=ab"}, "b", "", hashlib.sha256
            )
        )
        self.assertFalse(
            is_hmac_signature_valid(
                {"X-Hub-Signature-256": "sha256=zzz"}, "b", "s", hashlib.sha256
            )
        )

    def test_verify_signature_bearer(self):
        self.assertTrue(
            execute_signature_verification(
                "bearer", {"Authorization": "Bearer k"}, "", secret="k"
            )
        )

    def test_verify_signature_hmac_256_and_512(self):
        body = "abc"
        self.assertTrue(
            execute_signature_verification(
                "hmac_sha256",
                {"X-Hub-Signature-256": "sha256=" + self._hex("s", body)},
                body,
                secret="s",
            )
        )
        self.assertTrue(
            execute_signature_verification(
                "hmac_sha512",
                {
                    "X-Hub-Signature-512": "sha512="
                    + self._hex("s", body, hashlib.sha512)
                },
                body,
                secret="s",
            )
        )

    def test_verify_signature_unknown_and_custom_without_method(self):
        self.assertFalse(execute_signature_verification("bogus", {}, ""))
        self.assertFalse(execute_signature_verification("custom", {}, ""))

    def test_timestamp_valid_epoch_int_and_str(self):
        now = int(time.time())
        self.assertTrue(is_timestamp_valid(now))
        self.assertTrue(is_timestamp_valid(str(now)))

    def test_timestamp_valid_iso(self):
        self.assertTrue(is_timestamp_valid(datetime.now(tz=UTC).isoformat()))

    def test_timestamp_rejects_out_of_bounds(self):
        self.assertFalse(is_timestamp_valid(-1))
        self.assertFalse(is_timestamp_valid(253402300800))

    def test_timestamp_rejects_too_old(self):
        self.assertFalse(
            is_timestamp_valid(int(time.time()) - 10_000, max_age_seconds=300)
        )

    def test_timestamp_rejects_future(self):
        self.assertFalse(
            is_timestamp_valid(int(time.time()) + 10_000, future_tolerance_seconds=5)
        )

    def test_timestamp_rejects_invalid_type(self):
        self.assertFalse(is_timestamp_valid(None))


class TestVerifyCustomPrefixGate(TransactionCase):
    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_non_verify_method_rejected(self):
        result = _execute_custom_verification(
            "res.partner.search_count", {}, "{}", env=self.env
        )
        self.assertFalse(result)

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_private_non_verify_method_rejected(self):
        result = _execute_custom_verification(
            "res.partner._compute_display_name", {}, "{}", env=self.env
        )
        self.assertFalse(result)

    def test_verify_method_invoked(self):
        calls = []

        def fake_verify(model_self, headers, body):
            calls.append((headers, body))
            return True

        partner_cls = type(self.env["res.partner"])
        with patch.object(
            partner_cls, "verify_test_webhook", create=True, new=fake_verify
        ):
            result = _execute_custom_verification(
                "res.partner.verify_test_webhook",
                {"X-Test": "1"},
                "body",
                env=self.env,
            )
        self.assertTrue(result)
        self.assertEqual(calls, [({"X-Test": "1"}, "body")])
