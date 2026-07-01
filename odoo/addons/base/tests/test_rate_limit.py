from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestRateLimit(TransactionCase):
    """Test the core rate limiting mechanism provided by `rate.limit.log`."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.RateLimitLog = cls.env['rate.limit.log'].sudo()

    def test_consume_rate_limit_allows_and_blocks(self):
        self.assertTrue(self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}]))
        self.assertTrue(self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}]))
        self.assertFalse(self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}]))
        self.assertTrue(self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_2'], 'limit': 2, 'interval': 3600}]))
        self.assertTrue(self.RateLimitLog._consume_rate_limit([{'scope': 'signup', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}]))

    def test_consume_rate_limit_no_log_on_block(self):
        rate_limit_rules = [{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}]
        self.RateLimitLog._consume_rate_limit(rate_limit_rules)
        self.RateLimitLog._consume_rate_limit(rate_limit_rules)
        count_before = self.RateLimitLog.search_count([('rate_limit_key', '=', 'login-user_1')])
        self.RateLimitLog._consume_rate_limit(rate_limit_rules)
        count_after = self.RateLimitLog.search_count([('rate_limit_key', '=', 'login-user_1')])
        self.assertEqual(count_before, count_after)

    def test_consume_rate_limit_creates_log_on_allow(self):
        count_before = self.RateLimitLog.search_count([])
        self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}])
        count_after = self.RateLimitLog.search_count([])
        self.assertEqual(count_after, count_before + 1)

    def test_reset_rate_limit_clears_entries_and_allows_again(self):
        self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}])
        self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}])
        self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_2'], 'limit': 2, 'interval': 3600}])
        self.assertFalse(self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}]))
        self.RateLimitLog._reset_rate_limit([{'scope': 'login', 'key_vals': ['user_1']}])
        self.assertTrue(self.RateLimitLog._consume_rate_limit([{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}]))
        self.assertEqual(self.RateLimitLog.search_count([('rate_limit_key', '=', 'login-user_2')]), 1)

    def test_consume_rate_limit_counts_only_entries_within_interval(self):
        INTERVAL = 3600
        old_date = datetime.now() - timedelta(seconds=INTERVAL + 1)
        rate_limit_rules = [{'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600}]
        with (
            freeze_time(old_date),
            patch.object(self.env.cr, '_now', old_date),
        ):
            self.RateLimitLog._consume_rate_limit(rate_limit_rules)
            self.RateLimitLog._consume_rate_limit(rate_limit_rules)
        self.assertTrue(self.RateLimitLog._consume_rate_limit(rate_limit_rules))
        self.assertTrue(self.RateLimitLog._consume_rate_limit(rate_limit_rules))
        self.assertFalse(self.RateLimitLog._consume_rate_limit(rate_limit_rules))

    def test_consume_rate_limit_one_rule_fails_blocks_all(self):
        self.assertTrue(self.RateLimitLog._consume_rate_limit([
            {'scope': 'login', 'key_vals': ['127.0.0.0'], 'limit': 5, 'interval': 3600},
            {'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 3600},
        ]))
        self.assertTrue(self.RateLimitLog._consume_rate_limit([
            {'scope': 'login', 'key_vals': ['127.0.0.0'], 'limit': 5, 'interval': 3600},
            {'scope': 'login', 'key_vals': ['user_2'], 'limit': 2, 'interval': 3600},
        ]))
        self.assertTrue(self.RateLimitLog._consume_rate_limit([
            {'scope': 'login', 'key_vals': ['127.0.0.0'], 'limit': 5, 'interval': 3600},
            {'scope': 'login', 'key_vals': ['user_2'], 'limit': 2, 'interval': 3600},
        ]))
        self.assertFalse(self.RateLimitLog._consume_rate_limit([
            {'scope': 'login', 'key_vals': ['127.0.0.0'], 'limit': 5, 'interval': 3600},
            {'scope': 'login', 'key_vals': ['user_2'], 'limit': 2, 'interval': 3600},
        ]))

    def test_consume_rate_limit_does_not_duplicate_logs_for_same_key(self):
        rate_limit_rules = [
            {'scope': 'login', 'key_vals': ['user_1'], 'limit': 2, 'interval': 60},
            {'scope': 'login', 'key_vals': ['user_1'], 'limit': 50, 'interval': 3600},
        ]
        self.assertTrue(self.RateLimitLog._consume_rate_limit(rate_limit_rules))
        count = self.RateLimitLog.search_count([
            ('rate_limit_key', '=', 'login-user_1'),
        ])
        self.assertEqual(count, 1)
        self.assertTrue(self.RateLimitLog._consume_rate_limit(rate_limit_rules))
        count = self.RateLimitLog.search_count([
            ('rate_limit_key', '=', 'login-user_1'),
        ])
        self.assertEqual(count, 2)
        self.assertFalse(self.RateLimitLog._consume_rate_limit(rate_limit_rules))
