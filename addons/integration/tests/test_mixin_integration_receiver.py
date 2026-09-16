import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

from odoo.libs.logging import mute_logger
from odoo.tests.common import TransactionCase

from .common import APITransportTestCase
from odoo.addons.integration.tools import (
    compute_payload_hash,
    inspect_content_type,
    inspect_json_payload,
    inspect_payload_size,
    redact_error_message,
)
from odoo.addons.integration.tools.authentication import (
    is_bearer_token_valid,
    is_hmac_signature_valid,
    is_timestamp_valid,
)


class TestVerifyBearerToken(TransactionCase):
    def test_valid_bearer_token(self):
        headers = {"Authorization": "Bearer my_secret_token"}
        self.assertTrue(is_bearer_token_valid(headers, "my_secret_token"))

    def test_invalid_bearer_token(self):
        headers = {"Authorization": "Bearer wrong_token"}
        self.assertFalse(is_bearer_token_valid(headers, "my_secret_token"))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_missing_authorization_header(self):
        self.assertFalse(is_bearer_token_valid({}, "my_secret_token"))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_malformed_authorization_header(self):
        headers = {"Authorization": "Basic abc123"}
        self.assertFalse(is_bearer_token_valid(headers, "my_secret_token"))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_empty_bearer_token(self):
        headers = {"Authorization": "Bearer "}
        self.assertFalse(is_bearer_token_valid(headers, "my_secret_token"))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_no_expected_token(self):
        headers = {"Authorization": "Bearer some_token"}
        self.assertFalse(is_bearer_token_valid(headers, ""))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_non_dict_headers_rejected(self):
        self.assertFalse(is_bearer_token_valid("not a dict", "token"))


class TestVerifyHmacSignature(TransactionCase):
    def _sign(self, body, secret, hash_func=hashlib.sha256):
        return hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hash_func,
        ).hexdigest()

    def test_valid_hmac_sha256(self):
        secret = "test_secret"
        body = '{"event": "test"}'
        sig = self._sign(body, secret)
        headers = {"X-Hub-Signature-256": f"sha256={sig}"}

        self.assertTrue(is_hmac_signature_valid(headers, body, secret, hashlib.sha256))

    def test_invalid_hmac_sha256(self):
        body = '{"event": "test"}'
        sig = self._sign(body, "wrong_secret")
        headers = {"X-Hub-Signature-256": f"sha256={sig}"}

        self.assertFalse(
            is_hmac_signature_valid(headers, body, "correct_secret", hashlib.sha256)
        )

    def test_valid_hmac_sha512(self):
        secret = "test_secret"
        body = '{"event": "test"}'
        sig = self._sign(body, secret, hashlib.sha512)
        headers = {"X-Hub-Signature-512": f"sha512={sig}"}

        self.assertTrue(
            is_hmac_signature_valid(
                headers,
                body,
                secret,
                hashlib.sha512,
                signature_header="X-Hub-Signature-512",
                signature_prefix="sha512=",
            )
        )

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_missing_signature_header(self):
        self.assertFalse(is_hmac_signature_valid({}, "body", "secret", hashlib.sha256))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_no_secret_provided(self):
        headers = {"X-Hub-Signature-256": "sha256=abc"}
        self.assertFalse(is_hmac_signature_valid(headers, "body", "", hashlib.sha256))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_non_hex_signature_rejected(self):
        headers = {"X-Hub-Signature-256": "sha256=not_hex_zzzz"}
        self.assertFalse(
            is_hmac_signature_valid(headers, "body", "secret", hashlib.sha256)
        )

    def test_constant_time_comparison(self):
        secret = "test_secret"
        body = '{"data": "sensitive"}'
        sig = self._sign(body, secret)
        headers = {"X-Hub-Signature-256": f"sha256={sig}"}

        self.assertTrue(is_hmac_signature_valid(headers, body, secret, hashlib.sha256))


class TestVerifyTimestamp(TransactionCase):
    def test_current_unix_timestamp_valid(self):
        self.assertTrue(is_timestamp_valid(time.time(), max_age_seconds=300))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_old_unix_timestamp_rejected(self):
        old_ts = time.time() - 600
        self.assertFalse(is_timestamp_valid(old_ts, max_age_seconds=300))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_future_timestamp_rejected(self):
        future_ts = time.time() + 3600
        self.assertFalse(
            is_timestamp_valid(
                future_ts, max_age_seconds=300, future_tolerance_seconds=60
            )
        )

    def test_iso_string_timestamp_valid(self):
        now_iso = datetime.now(tz=UTC).isoformat()
        self.assertTrue(is_timestamp_valid(now_iso, max_age_seconds=300))

    def test_z_suffix_iso_string(self):
        now_iso = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertTrue(is_timestamp_valid(now_iso, max_age_seconds=300))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_negative_timestamp_rejected(self):
        self.assertFalse(is_timestamp_valid(-1))

    @mute_logger("odoo.addons.integration.tools.authentication")
    def test_invalid_type_rejected(self):
        self.assertFalse(is_timestamp_valid([123]))


class TestValidatePayload(TransactionCase):
    def test_valid_json_payload(self):
        is_valid, parsed, error = inspect_json_payload('{"key": "value"}')
        self.assertTrue(is_valid)
        self.assertEqual(parsed["key"], "value")
        self.assertIsNone(error)

    def test_invalid_json_payload(self):
        is_valid, parsed, error = inspect_json_payload("not valid json")
        self.assertFalse(is_valid)
        self.assertIsNone(parsed)
        self.assertIn("Invalid JSON", error)

    def test_empty_payload_rejected(self):
        is_valid, _parsed, _error = inspect_json_payload("")
        self.assertFalse(is_valid)

    def test_deeply_nested_payload_rejected(self):
        payload = {"level": 0}
        current = payload
        for i in range(200):
            current["nested"] = {"level": i + 1}
            current = current["nested"]
        is_valid, _, error = inspect_json_payload(json.dumps(payload), max_depth=100)
        self.assertFalse(is_valid)
        self.assertIn("depth", error)

    def test_payload_size_validation(self):
        small = b'{"ok": true}'
        is_valid, error = inspect_payload_size(small, max_size_bytes=1024)
        self.assertTrue(is_valid)

        large = b"x" * 2048
        is_valid, error = inspect_payload_size(large, max_size_bytes=1024)
        self.assertFalse(is_valid)
        self.assertIn("too large", error)

    def test_content_type_validation(self):
        is_valid, _ = inspect_content_type("application/json")
        self.assertTrue(is_valid)

        is_valid, _error = inspect_content_type("text/plain")
        self.assertFalse(is_valid)

        is_valid, _ = inspect_content_type("application/json; charset=utf-8")
        self.assertTrue(is_valid)

        is_valid, _error = inspect_content_type(None)
        self.assertFalse(is_valid)


class TestPayloadHash(TransactionCase):
    def test_dict_hash_deterministic(self):
        h1 = compute_payload_hash({"b": 2, "a": 1})
        h2 = compute_payload_hash({"a": 1, "b": 2})
        self.assertEqual(h1, h2)

    def test_string_hash_normalizes_json(self):
        h1 = compute_payload_hash('{"b": 2, "a": 1}')
        h2 = compute_payload_hash('{"a": 1, "b": 2}')
        self.assertEqual(h1, h2)

    def test_different_payloads_different_hash(self):
        h1 = compute_payload_hash({"a": 1})
        h2 = compute_payload_hash({"a": 2})
        self.assertNotEqual(h1, h2)


class TestSanitizeErrorMessage(TransactionCase):
    def test_the_value_after_a_mixed_case_password_label_is_masked(self):
        result = redact_error_message("Invalid Password: abc123")
        self.assertNotIn("abc123", result)
        self.assertIn("***REDACTED***", result)

    def test_the_value_after_an_uppercase_token_label_is_masked(self):
        result = redact_error_message("Expired TOKEN=XYZ987")
        self.assertNotIn("XYZ987", result)

    def test_a_secret_with_a_known_shape_is_masked_without_a_label(self):
        key_id = "AKIA" + "ABCDEFGHIJKLMNOP"
        self.assertNotIn(key_id, redact_error_message(f"S3 refused {key_id}"))

    def test_truncates_long_message(self):
        long_msg = "x" * 1000
        result = redact_error_message(long_msg, max_length=100)
        self.assertLessEqual(len(result), 120)

    def test_accepts_exception(self):
        result = redact_error_message(ValueError("bad token: s3cr3tvalue"))
        self.assertNotIn("s3cr3tvalue", result)


class TestChannelMixinRateLimit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["integration.service"].create(
            {
                "name": "Test Service",
                "code": "test_rate_limit",
                "endpoint_url": "https://api.test.com",
            },
        )

    def test_calculate_retry_delay_fixed(self):
        self.service.retry_backoff_type = "fixed"
        self.service.retry_initial_delay = 30
        self.assertEqual(self.service.get_retry_delay(1), 30)
        self.assertEqual(self.service.get_retry_delay(5), 30)

    def test_calculate_retry_delay_linear(self):
        self.service.retry_backoff_type = "linear"
        self.service.retry_initial_delay = 30
        self.assertEqual(self.service.get_retry_delay(1), 30)
        self.assertEqual(self.service.get_retry_delay(3), 90)

    def test_calculate_retry_delay_exponential(self):
        self.service.retry_backoff_type = "exponential"
        self.service.retry_initial_delay = 60
        self.assertEqual(self.service.get_retry_delay(1), 60)
        self.assertEqual(self.service.get_retry_delay(2), 120)
        self.assertEqual(self.service.get_retry_delay(3), 240)

    def test_should_retry_enabled(self):
        self.service.retry_enabled = True
        self.service.retry_max_attempts = 3
        self.assertTrue(self.service.is_retry_required(1))
        self.assertTrue(self.service.is_retry_required(2))
        self.assertFalse(self.service.is_retry_required(3))

    def test_should_retry_disabled(self):
        self.service.retry_enabled = False
        self.assertFalse(self.service.is_retry_required(1))


class TestRateLimitStrictPosture(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.outbound = cls.env["integration.service"].create(
            {
                "name": "Strictness Probe",
                "code": "strictness_probe",
                "endpoint_url": "https://api.test.com",
                "rate_limit_enabled": True,
                "rate_limit_requests": 5,
                "rate_limit_period": "minute",
            }
        )

    def _consumed_strict(self, endpoint):
        seen = []
        bucket_model = self.env["rate.limit.bucket"]
        original = type(bucket_model).consume_token

        def spy(bucket_self, strict=False):
            seen.append(strict)
            return original(bucket_self, strict=strict)

        self.patch(type(bucket_model), "consume_token", spy)
        endpoint.check_rate_limit()
        self.assertEqual(len(seen), 1, "expected exactly one bucket consumption")
        return seen[0]

    def test_field_is_declared_on_the_mixin(self):
        self.assertIn(
            "rate_limit_strict", self.env["mixin.integration.channel"]._fields
        )
        self.assertIn(
            "rate_limit_strict", self.env["mixin.integration.receiver"]._fields
        )
        self.assertIn("rate_limit_strict", self.env["integration.service"]._fields)

    def test_inbound_defaults_to_fail_closed(self):
        defaults = self.env["mixin.integration.receiver"].default_get(
            ["rate_limit_strict"]
        )
        self.assertIs(defaults["rate_limit_strict"], True)

    def test_inbound_default_overrides_the_mixin(self):
        mixin_defaults = self.env["mixin.integration.channel"].default_get(
            ["rate_limit_strict"]
        )
        self.assertIs(mixin_defaults["rate_limit_strict"], False)

    def test_outbound_defaults_to_fail_open(self):
        self.assertFalse(self.outbound.rate_limit_strict)

    def test_limiter_reads_the_flag_off_a_real_record(self):
        self.assertFalse(self._consumed_strict(self.outbound))
        self.outbound.rate_limit_strict = True
        self.assertTrue(self._consumed_strict(self.outbound))


class TestPayloadLogLimit(TransactionCase):
    def _endpoint(self, **overrides):
        vals = {"processing_mode": "sync", "log_request_payload_max_bytes": 64}
        vals.update(overrides)
        return self.env["mixin.integration.receiver"].new(vals)

    def test_a_declared_limit_is_reported(self):
        self.assertEqual(self._endpoint()._payload_log_limit(), 64)

    def test_no_limit_is_the_default(self):
        self.assertEqual(
            self.env["mixin.integration.receiver"].default_get(
                ["log_request_payload_max_bytes"]
            )["log_request_payload_max_bytes"],
            0,
        )

    def test_an_async_endpoint_ignores_the_limit(self):
        endpoint = self._endpoint(processing_mode="async")

        self.assertEqual(endpoint.log_request_payload_max_bytes, 64)
        self.assertEqual(endpoint._payload_log_limit(), 0)

    def test_a_nonsensical_negative_limit_reads_as_no_limit(self):
        self.assertEqual(
            self._endpoint(log_request_payload_max_bytes=-5)._payload_log_limit(), 0
        )


class TestPayloadHashOverride(APITransportTestCase):
    def _log(self, **vals):
        base = {
            "direction": "outbound",
            "state": "pending",
            "channel_id": f"integration.service,{self.service_stripe.id}",
        }
        base.update(vals)
        return self.env["integration.exchange"].create(base)

    def test_the_hash_is_derived_from_the_stored_body_by_default(self):
        body = '{"b": 2, "a": 1}'

        self.assertEqual(
            self._log(request_payload=body).request_payload_hash,
            compute_payload_hash(body),
        )

    def test_key_order_does_not_change_the_hash(self):
        first = self._log(request_payload='{"a": 1, "b": 2}')
        second = self._log(request_payload='{"b": 2, "a": 1}')

        self.assertEqual(first.request_payload_hash, second.request_payload_hash)

    def test_an_override_wins_over_the_stored_body(self):
        received = '{"audio_b64": "' + "A" * 200 + '"}'
        placeholder = '{"_omitted": {"bytes": 216}}'

        event = self._log(
            request_payload=placeholder,
            request_payload_hash_override=compute_payload_hash(received),
            request_payload_omitted_bytes=len(received),
        )

        self.assertEqual(event.request_payload_hash, compute_payload_hash(received))
        self.assertNotEqual(
            event.request_payload_hash, compute_payload_hash(placeholder)
        )

    def test_the_recorded_size_describes_the_request_not_the_placeholder(self):
        event = self._log(
            request_payload='{"_omitted": {"bytes": 5000}}',
            request_payload_omitted_bytes=5000,
        )

        self.assertEqual(event.request_payload_size, 5000)

    def test_an_unparseable_body_still_hashes(self):
        event = self._log(request_payload="not json at all")

        self.assertEqual(
            event.request_payload_hash, compute_payload_hash("not json at all")
        )
