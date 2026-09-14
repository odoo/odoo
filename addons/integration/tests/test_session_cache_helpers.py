from odoo.tests import TransactionCase, tagged

from odoo.addons.integration.tools.session_cache import (
    SessionCache,
    get_session_cache,
    invalidate_session_cache,
)


@tagged("post_install", "-at_install")
class TestSessionCacheHelpers(TransactionCase):
    def test_get_session_cache_returns_singleton(self):
        first = get_session_cache(self.env)
        second = get_session_cache(self.env)
        self.assertIs(first, second)

    def test_invalidate_matching_removes_only_matches(self):
        cache = SessionCache(max_size=10)
        cache.set("stripe:1", "a")
        cache.set("stripe:2", "b")
        cache.set("slack:1", "c")
        removed = cache.invalidate_matching(lambda key: key.startswith("stripe:"))
        self.assertEqual(removed, 2)
        self.assertIsNone(cache.get("stripe:1"))
        self.assertIsNotNone(cache.get("slack:1"))

    def test_invalidate_session_cache_clears_entries(self):
        cache = get_session_cache(self.env)
        cache.set("key", "value")
        invalidate_session_cache(self.env)
        self.assertIsNone(cache.get("key"))
