from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import psycopg

from odoo import fields
from odoo.exceptions import UserError
from odoo.libs.logging import mute_logger
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.rate_limit.tools import EndpointRateLimiter


class TestRateLimitBucket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.MockEndpoint = cls.env["res.partner"]

    def test_bucket_creation(self):
        endpoint = self.MockEndpoint.create({"name": "Test Endpoint"})

        bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": "test_bucket_key",
                "endpoint_model": endpoint._name,
                "endpoint_id": endpoint.id,
                "tokens": 100.0,
            },
        )

        self.assertEqual(bucket.bucket_key, "test_bucket_key")
        self.assertEqual(bucket.tokens, 100.0)
        self.assertTrue(bucket.last_refill)

    def test_bucket_reset(self):
        endpoint = self.MockEndpoint.create({"name": "Test Endpoint Reset"})

        bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": "test_bucket_reset",
                "endpoint_model": endpoint._name,
                "endpoint_id": endpoint.id,
                "tokens": 0.0,
            },
        )

        self.assertEqual(bucket.tokens, 0.0)

        bucket.reset_bucket()

        self.assertGreater(bucket.tokens, 0)

    def test_bucket_reset_namespace_subject_is_blocked(self):
        bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": "test_bucket_reset_namespace",
                "endpoint_model": "rate_limit.test.namespace",
                "endpoint_id": 999,
                "tokens": 0.0,
            },
        )

        self.assertFalse(bucket.can_reset)
        with self.assertRaises(UserError):
            bucket.reset_bucket()

    def test_bucket_cleanup(self):
        endpoint = self.MockEndpoint.create({"name": "Test Endpoint Cleanup"})

        old_date = fields.Datetime.now() - timedelta(days=31)

        bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": "test_bucket_cleanup_old",
                "endpoint_model": endpoint._name,
                "endpoint_id": endpoint.id,
                "tokens": 100.0,
                "last_request_at": old_date,
            },
        )

        bucket_id = bucket.id

        count = self.env["rate.limit.bucket"].cron_gc_old_buckets()

        self.assertGreaterEqual(count, 1)

        remaining = self.env["rate.limit.bucket"].search([("id", "=", bucket_id)])
        self.assertFalse(remaining)

    def test_bucket_company_rule(self):
        rule = self.env["ir.rule"].search(
            [
                ("model_id.model", "=", "rate.limit.bucket"),
                ("name", "ilike", "multi-company"),
            ],
        )
        self.assertTrue(rule, "Rate limit bucket should have a multi-company rule")


class TestRateLimitBucketTokenConsumption(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.MockEndpoint = cls.env["res.partner"]

    def test_consume_token_success(self):
        endpoint = self.MockEndpoint.create({"name": "Test Consume"})

        bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": "test_consume_success",
                "endpoint_model": endpoint._name,
                "endpoint_id": endpoint.id,
                "tokens": 10.0,
            },
        )

        initial_tokens = bucket.tokens

        result = bucket.consume_token()

        self.assertTrue(result)
        bucket.invalidate_recordset()
        self.assertLess(bucket.tokens, initial_tokens)

    def test_consume_token_empty_bucket(self):
        endpoint = self.MockEndpoint.create({"name": "Test Consume Empty"})

        bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": "test_consume_empty",
                "endpoint_model": endpoint._name,
                "endpoint_id": endpoint.id,
                "tokens": 0.0,
            },
        )

        result = bucket.consume_token()

        self.assertFalse(result)

    def _make_bucket(self, name):
        endpoint = self.MockEndpoint.create({"name": f"Endpoint for {name}"})
        return self.env["rate.limit.bucket"].create(
            {
                "bucket_key": name,
                "endpoint_model": endpoint._name,
                "endpoint_id": endpoint.id,
                "tokens": 10.0,
            },
        )

    def test_consume_token_fail_open_on_exception(self):
        bucket = self._make_bucket("strict_mode_fail_open")

        def _explode(self_):
            raise RuntimeError("simulated bucket failure")

        with patch.object(
            type(bucket),
            "_get_endpoint_config",
            _explode,
        ):
            result = bucket.consume_token()
        self.assertTrue(result, "Default mode must fail OPEN (allow request)")

    def test_consume_token_fail_closed_on_exception_strict(self):
        bucket = self._make_bucket("strict_mode_fail_closed")

        def _explode(self_):
            raise RuntimeError("simulated bucket failure")

        with patch.object(
            type(bucket),
            "_get_endpoint_config",
            _explode,
        ):
            result = bucket.consume_token(strict=True)
        self.assertFalse(result, "Strict mode must fail CLOSED (deny request)")


class TestEndpointRateLimiterStrictMode(TransactionCase):
    def test_endpoint_rate_limiter_reads_strict_flag(self):
        strict_endpoint = SimpleNamespace(
            _name="res.partner",
            id=1,
            rate_limit_enabled=True,
            rate_limit_requests=100,
            rate_limit_period="minute",
            rate_limit_strict=True,
        )
        lax_endpoint = SimpleNamespace(
            _name="res.partner",
            id=2,
            rate_limit_enabled=True,
            rate_limit_requests=100,
            rate_limit_period="minute",
        )

        fake_bucket_model = MagicMock()
        fake_bucket_model.consume_for.return_value = True

        fake_env = MagicMock()
        fake_env.__getitem__.return_value = fake_bucket_model

        limiter = EndpointRateLimiter(fake_env, strict_endpoint)
        limiter.check_limit()
        fake_bucket_model.consume_for.assert_called_with(
            strict_endpoint, None, strict=True
        )

        fake_bucket_model.reset_mock()

        limiter = EndpointRateLimiter(fake_env, lax_endpoint)
        limiter.check_limit()
        fake_bucket_model.consume_for.assert_called_with(
            lax_endpoint, None, strict=False
        )

    def test_consume_for_forwards_strict_to_the_bucket(self):
        endpoint = self.env["res.partner"].create({"name": "consume-for probe"})
        bucket_model = self.env["rate.limit.bucket"]

        with patch.object(type(bucket_model), "get_or_create_bucket") as get_or_create:
            bucket = MagicMock()
            bucket.consume_token.return_value = True
            get_or_create.return_value = bucket

            self.assertTrue(bucket_model.consume_for(endpoint, None, strict=True))
            bucket.consume_token.assert_called_with(strict=True)

            bucket.reset_mock()
            bucket_model.consume_for(endpoint, 7, strict=False)
            bucket.consume_token.assert_called_with(strict=False)
            self.assertEqual(get_or_create.call_args[0][1], 7)


@tagged("post_install", "-at_install")
class TestRateLimitBucketContention(TransactionCase):
    """A row conflict is not a verdict on the caller's quota.

    Every cursor here is REPEATABLE READ and the strict path takes `FOR UPDATE`
    on one hot row under a `lock_timeout`, so concurrency produces exactly the
    three errors the framework calls retryable. Swallowing one into a refusal
    made the stricter setting fail harder the more load it saw.
    """

    def setUp(self):
        super().setUp()
        endpoint = self.env["res.partner"].create({"name": "contention probe"})
        self.bucket = self.env["rate.limit.bucket"].create(
            {
                "bucket_key": "contention.probe",
                "endpoint_model": endpoint._name,
                "endpoint_id": endpoint.id,
                "tokens": 100.0,
            }
        )

    def _raise_on_lock(self, error):
        def _lock(_self, strict):
            raise error

        self.patch(self.registry["rate.limit.bucket"], "_lock_bucket_row", _lock)

    @mute_logger("odoo.addons.rate_limit.models.rate_limit_bucket")
    def test_a_serialization_failure_is_reraised_not_denied(self):
        self._raise_on_lock(psycopg.errors.SerializationFailure("40001"))

        with self.assertRaises(psycopg.errors.SerializationFailure):
            self.bucket.consume_token(strict=True)

    @mute_logger("odoo.addons.rate_limit.models.rate_limit_bucket")
    def test_a_lock_timeout_is_reraised_not_denied(self):
        # The strict path sets `lock_timeout`, so this is the error IT produces.
        self._raise_on_lock(psycopg.errors.LockNotAvailable("55P03"))

        with self.assertRaises(psycopg.errors.LockNotAvailable):
            self.bucket.consume_token(strict=True)

    @mute_logger("odoo.addons.rate_limit.models.rate_limit_bucket")
    def test_a_deadlock_is_reraised_not_denied(self):
        self._raise_on_lock(psycopg.errors.DeadlockDetected("40P01"))

        with self.assertRaises(psycopg.errors.DeadlockDetected):
            self.bucket.consume_token(strict=True)

    @mute_logger("odoo.addons.rate_limit.models.rate_limit_bucket")
    def test_a_real_error_still_denies_in_strict_mode(self):
        # The re-raise must not swallow the fail-closed behaviour it sits above:
        # an error that is NOT a row conflict still denies under strict.
        self._raise_on_lock(ValueError("something actually wrong"))

        self.assertFalse(self.bucket.consume_token(strict=True))

    @mute_logger("odoo.addons.rate_limit.models.rate_limit_bucket")
    def test_a_real_error_still_allows_when_not_strict(self):
        self._raise_on_lock(ValueError("something actually wrong"))

        self.assertTrue(self.bucket.consume_token(strict=False))
