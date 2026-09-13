"""`consume_for_key`: rate-limiting a subject that is not an endpoint record.

`consume_for` needs something with `_name`, `id` and `rate_limit_requests`,
which is right when the subject is a configured endpoint and wrong for the three
subjects that turned up anyway -- a user id, a peer address and a chat. Both
callers that had one fabricated a `SimpleNamespace` carrying exactly those
attributes to get past the signature, independently of each other. These tests
exercise the entry point meant to replace both fakes.
"""

from odoo.tests import TransactionCase, tagged

_KEY = "test.subject:keyed:global"


@tagged("post_install", "-at_install")
class TestConsumeForKey(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Bucket = self.env["rate.limit.bucket"]
        self.addCleanup(self._drop)

    def _drop(self):
        self.env.cr.execute(
            "DELETE FROM rate_limit_bucket WHERE bucket_key LIKE 'test.subject:%'"
        )

    def _bucket(self, key=_KEY):
        return self.Bucket.search([("bucket_key", "=", key)], limit=1)

    def test_no_record_is_needed(self):
        """The whole point: a namespace and an id, not a browsable model."""
        allowed = self.Bucket.consume_for_key(
            _KEY, subject_model="test.subject", subject_id=7, capacity=3
        )

        self.assertTrue(allowed)
        bucket = self._bucket()
        self.assertEqual(bucket.endpoint_model, "test.subject")
        self.assertEqual(bucket.endpoint_id, 7)
        self.assertEqual(bucket.tokens, 2.0)

    def test_it_refuses_at_the_capacity(self):
        verdicts = [
            self.Bucket.consume_for_key(
                _KEY, subject_model="test.subject", subject_id=7, capacity=3
            )
            for _ in range(5)
        ]
        self.assertEqual(verdicts[:3], [True, True, True])
        self.assertIn(False, verdicts, f"the capacity never bit: {verdicts}")

    def test_subjects_do_not_share_a_bucket(self):
        for _ in range(3):
            self.Bucket.consume_for_key(
                _KEY, subject_model="test.subject", subject_id=7, capacity=3
            )
        self.assertFalse(
            self.Bucket.consume_for_key(
                _KEY, subject_model="test.subject", subject_id=7, capacity=3
            )
        )

        self.assertTrue(
            self.Bucket.consume_for_key(
                "test.subject:other:global",
                subject_model="test.subject",
                subject_id=8,
                capacity=3,
            ),
            "a second subject must not inherit the first one's exhaustion",
        )

    def test_refill_rate_defaults_to_one_capacity_per_window(self):
        """A caller states a window; the per-second rate is arithmetic.

        Both callers were computing `limit / window` at the call site, which is
        the kind of thing that is right in one place and wrong in the other.
        """
        self.Bucket.consume_for_key(
            _KEY,
            subject_model="test.subject",
            subject_id=7,
            capacity=60,
            window_seconds=60,
        )
        bucket = self._bucket()

        # 59 left, and a full window would restore exactly the 60 it started at.
        self.assertEqual(bucket.tokens, 59.0)
        self.assertEqual(
            bucket._refilled_tokens(
                0.0,
                bucket.last_refill,
                bucket.last_refill.replace(microsecond=0),
                capacity=60,
                refill_rate=1.0,
            ),
            0.0,
        )

    def test_an_existing_bucket_is_reused_not_duplicated(self):
        for _ in range(2):
            self.Bucket.consume_for_key(
                _KEY, subject_model="test.subject", subject_id=7, capacity=5
            )

        self.env.cr.execute(
            "SELECT count(*) FROM rate_limit_bucket WHERE bucket_key = %s", (_KEY,)
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1)
