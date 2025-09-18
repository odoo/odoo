"""Unit tests for odoo.libs.res_users — no Odoo ORM dependency."""

import hmac
import unittest
from hashlib import sha256

from odoo.libs.res_users import (
    compute_legacy_session_token_hash,
    compute_session_token_hash,
)


class TestComputeSessionTokenHash(unittest.TestCase):
    """Test compute_session_token_hash pure function."""

    def test_returns_hex_digest(self):
        result = compute_session_token_hash(
            "sid123", [("login", "admin"), ("passwd", "secret")]
        )
        self.assertEqual(len(result), 64)  # SHA-256 hex digest length
        self.assertTrue(all(c in "0123456789abcdef" for c in result))

    def test_empty_field_values_returns_false(self):
        result = compute_session_token_hash("sid123", [])
        self.assertIs(result, False)

    def test_false_field_values_returns_false(self):
        """Non-existing users pass False instead of an iterable."""
        result = compute_session_token_hash("sid123", False)
        self.assertIs(result, False)

    def test_filters_none_values(self):
        """Fields with None values should not affect the key."""
        with_none = compute_session_token_hash(
            "sid123",
            [("login", "admin"), ("new_field", None)],
        )
        without_none = compute_session_token_hash(
            "sid123",
            [("login", "admin")],
        )
        self.assertEqual(with_none, without_none)

    def test_deterministic(self):
        fields = [("login", "admin"), ("passwd", "secret")]
        r1 = compute_session_token_hash("sid123", fields)
        r2 = compute_session_token_hash("sid123", fields)
        self.assertEqual(r1, r2)

    def test_different_sid_different_hash(self):
        fields = [("login", "admin")]
        r1 = compute_session_token_hash("sid123", fields)
        r2 = compute_session_token_hash("sid456", fields)
        self.assertNotEqual(r1, r2)

    def test_matches_manual_hmac(self):
        """Verify the output matches a manually computed HMAC-SHA256."""
        sid = "test-session"
        field_values = [("login", "admin"), ("passwd", "pwd")]
        key_tuple = tuple((k, v) for k, v in field_values if v is not None)
        key = str(key_tuple).encode()
        expected = hmac.new(key, sid.encode(), sha256).hexdigest()
        self.assertEqual(compute_session_token_hash(sid, field_values), expected)


class TestComputeLegacySessionTokenHash(unittest.TestCase):
    """Test compute_legacy_session_token_hash pure function."""

    def test_returns_hex_digest(self):
        result = compute_legacy_session_token_hash("sid123", [("login", "admin")])
        self.assertEqual(len(result), 64)

    def test_empty_field_values_returns_false(self):
        result = compute_legacy_session_token_hash("sid123", [])
        self.assertIs(result, False)

    def test_false_field_values_returns_false(self):
        """Non-existing users pass False instead of an iterable."""
        result = compute_legacy_session_token_hash("sid123", False)
        self.assertIs(result, False)

    def test_uses_values_only(self):
        """Legacy key is derived from values only, not column names."""
        r1 = compute_legacy_session_token_hash("sid", [("login", "admin")])
        r2 = compute_legacy_session_token_hash("sid", [("different_name", "admin")])
        self.assertEqual(r1, r2)

    def test_different_from_new_method(self):
        """Legacy and new methods should produce different tokens."""
        fields = [("login", "admin"), ("passwd", "secret")]
        new_result = compute_session_token_hash("sid", fields)
        legacy_result = compute_legacy_session_token_hash("sid", fields)
        self.assertNotEqual(new_result, legacy_result)

    def test_matches_manual_hmac(self):
        """Verify output matches manually computed legacy HMAC."""
        sid = "test-session"
        field_values = [("login", "admin"), ("passwd", "pwd")]
        key = f"{tuple(f[1] for f in field_values)}".encode()
        expected = hmac.new(key, sid.encode(), sha256).hexdigest()
        self.assertEqual(compute_legacy_session_token_hash(sid, field_values), expected)


if __name__ == "__main__":
    unittest.main()
