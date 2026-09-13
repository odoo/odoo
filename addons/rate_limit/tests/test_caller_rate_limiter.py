import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

from odoo.tests.common import BaseCase

from odoo.addons.rate_limit.tools.caller_rate_limiter import (
    SlidingWindowLimiter,
    get_caller_rate_limiter,
)


class TestSlidingWindowLimiter(BaseCase):
    def setUp(self):
        super().setUp()
        self.limiter = SlidingWindowLimiter()

    def test_init(self):
        limiter = SlidingWindowLimiter()
        self.assertEqual(len(limiter._attempts), 0)

    def test_first_request_allowed(self):
        result = self.limiter.check(
            (1, 1, "read"),
            limit=10,
            window_seconds=60 * 60,
        )

        self.assertTrue(result["allowed"])
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["limit"], 10)

    def test_rate_limit_enforced(self):
        for i in range(5):
            result = self.limiter.check(
                (1, 1, "read"),
                limit=5,
                window_seconds=60 * 60,
            )
            self.assertTrue(result["allowed"], f"Request {i + 1} should be allowed")

        result = self.limiter.check(
            (1, 1, "read"),
            limit=5,
            window_seconds=60 * 60,
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["attempts"], 5)

    def test_different_credentials_separate_limits(self):
        for _ in range(5):
            self.limiter.check(
                (1, 1, "read"),
                limit=5,
                window_seconds=60 * 60,
            )

        result1 = self.limiter.check(
            (1, 1, "read"),
            limit=5,
            window_seconds=60 * 60,
        )
        self.assertFalse(result1["allowed"])

        result2 = self.limiter.check(
            (2, 1, "read"),
            limit=5,
            window_seconds=60 * 60,
        )
        self.assertTrue(result2["allowed"])

    def test_different_users_separate_limits(self):
        for _ in range(5):
            self.limiter.check(
                (1, 1, "read"),
                limit=5,
                window_seconds=60 * 60,
            )

        result1 = self.limiter.check(
            (1, 1, "read"),
            limit=5,
            window_seconds=60 * 60,
        )
        self.assertFalse(result1["allowed"])

        result2 = self.limiter.check(
            (1, 2, "read"),
            limit=5,
            window_seconds=60 * 60,
        )
        self.assertTrue(result2["allowed"])

    def test_different_operations_separate_limits(self):
        for _ in range(5):
            self.limiter.check(
                (1, 1, "read"),
                limit=5,
                window_seconds=60 * 60,
            )

        result_read = self.limiter.check(
            (1, 1, "read"),
            limit=5,
            window_seconds=60 * 60,
        )
        self.assertFalse(result_read["allowed"])

        result_write = self.limiter.check(
            (1, 1, "write"),
            limit=5,
            window_seconds=60 * 60,
        )
        self.assertTrue(result_write["allowed"])

    def test_reset_limit(self):
        for _ in range(5):
            self.limiter.check(
                (1, 1, "read"),
                limit=5,
                window_seconds=60 * 60,
            )

        result = self.limiter.check(
            (1, 1, "read"),
            limit=5,
            window_seconds=60 * 60,
        )
        self.assertFalse(result["allowed"])

        self.limiter.reset((1, 1, "read"))

        result = self.limiter.check(
            (1, 1, "read"),
            limit=5,
            window_seconds=60 * 60,
        )
        self.assertTrue(result["allowed"])

    def test_get_stats(self):
        self.limiter.check((1, 1, "read"), limit=100, window_seconds=60 * 60)
        self.limiter.check((2, 1, "read"), limit=100, window_seconds=60 * 60)
        self.limiter.check((1, 2, "read"), limit=100, window_seconds=60 * 60)

        stats = self.limiter.get_stats()

        self.assertEqual(stats["total_keys"], 3)
        self.assertEqual(stats["total_attempts_tracked"], 3)

    def test_cleanup_old_entries(self):
        self.limiter.check((1, 1, "read"), limit=100, window_seconds=60 * 60)

        key = (1, 1, "read")
        old_time = datetime.now() - timedelta(hours=25)
        self.limiter._attempts[key] = [old_time]

        cleaned = self.limiter.cleanup_old_entries(max_age_hours=24)

        self.assertEqual(cleaned, 1)
        self.assertEqual(len(self.limiter._attempts), 0)

    def test_sliding_window(self):
        self.limiter.check((1, 1, "read"), limit=100, window_seconds=60 * 60)

        key = (1, 1, "read")
        old_time = datetime.now() - timedelta(minutes=61)
        self.limiter._attempts[key].insert(0, old_time)

        result = self.limiter.check((1, 1, "read"), limit=100, window_seconds=60 * 60)

        self.assertEqual(result["attempts"], 2)

    def test_thread_safety(self):
        errors = []
        results = []

        def worker(thread_id):
            try:
                for _ in range(10):
                    result = self.limiter.check(
                        (1, thread_id, "read"),
                        limit=100,
                        window_seconds=60 * 60,
                    )
                    results.append(result["allowed"])
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(len(errors), 0)
        self.assertTrue(all(results))

    def test_reset_at_calculation(self):
        result = self.limiter.check(
            (1, 1, "read"),
            limit=10,
            window_seconds=60 * 60,
        )

        self.assertIsNotNone(result["reset_at"])
        expected_reset = datetime.now() + timedelta(minutes=60)
        self.assertAlmostEqual(
            result["reset_at"].timestamp(),
            expected_reset.timestamp(),
            delta=5,
        )


class TestRateLimiterRegistry(BaseCase):
    def test_get_rate_limiter_creates_new(self):
        env = Mock()
        env.registry = Mock()
        env.cr.dbname = "test_db"

        if hasattr(env.registry, "_inbound_caller_rate_limiter"):
            del env.registry._inbound_caller_rate_limiter

        limiter = get_caller_rate_limiter(env)

        self.assertIsNotNone(limiter)
        self.assertIsInstance(limiter, SlidingWindowLimiter)
        self.assertTrue(hasattr(env.registry, "_inbound_caller_rate_limiter"))

    def test_get_rate_limiter_returns_existing(self):
        env = Mock()
        env.registry = Mock()
        env.cr.dbname = "test_db"

        if hasattr(env.registry, "_inbound_caller_rate_limiter"):
            del env.registry._inbound_caller_rate_limiter

        limiter1 = get_caller_rate_limiter(env)

        limiter2 = get_caller_rate_limiter(env)

        self.assertIs(limiter1, limiter2)


class TestRateLimiterMaxKeys(BaseCase):
    def test_max_keys_limit_enforced(self):
        limiter = SlidingWindowLimiter(max_keys=3)

        limiter.check((1, 1, "read"), limit=100, window_seconds=60 * 60)
        limiter.check((2, 1, "read"), limit=100, window_seconds=60 * 60)
        limiter.check((3, 1, "read"), limit=100, window_seconds=60 * 60)

        stats = limiter.get_stats()
        self.assertEqual(stats["total_keys"], 3)

        limiter.check((4, 1, "read"), limit=100, window_seconds=60 * 60)

        stats = limiter.get_stats()
        self.assertEqual(stats["total_keys"], 3)
        self.assertEqual(stats["max_keys"], 3)

    def test_eviction_preserves_recent_keys(self):
        limiter = SlidingWindowLimiter(max_keys=2)

        limiter.check((1, 1, "read"), limit=100, window_seconds=60 * 60)
        time.sleep(0.01)
        limiter.check((2, 1, "read"), limit=100, window_seconds=60 * 60)

        limiter.check((1, 1, "read"), limit=100, window_seconds=60 * 60)

        limiter.check((3, 1, "read"), limit=100, window_seconds=60 * 60)

        stats = limiter.get_stats()
        self.assertEqual(stats["total_keys"], 2)

    def test_memory_usage_pct(self):
        limiter = SlidingWindowLimiter(max_keys=100)

        for i in range(50):
            limiter.check((i, 1, "read"), limit=100, window_seconds=60 * 60)

        stats = limiter.get_stats()
        self.assertEqual(stats["memory_usage_pct"], 50.0)

    def test_default_max_keys(self):
        limiter = SlidingWindowLimiter()
        self.assertEqual(limiter._max_keys, 10000)
