"""Database-free tests for ``ir.mail_server`` pure functions.

Covers ``is_ascii()``, ``_parse_from_filter()``, and
``_match_from_filter()`` — all pure string/email matching logic.

Run with::

    python -m pytest core/tests/models/test_ir_mail_server.py -v
"""

from odoo.addons.base.models.ir_mail_server import is_ascii

# ── is_ascii() ────────────────────────────────────────────────


class TestIsAscii:
    """``is_ascii()``: check if all characters are below codepoint 128."""

    def test_plain_ascii(self):
        assert is_ascii("hello world") is True

    def test_empty_string(self):
        assert is_ascii("") is True

    def test_ascii_with_digits(self):
        assert is_ascii("test123!@#") is True

    def test_non_ascii_accent(self):
        assert is_ascii("café") is False

    def test_non_ascii_emoji(self):
        assert is_ascii("hello 😊") is False

    def test_boundary_character(self):
        """DEL (127) is the highest ASCII character."""
        assert is_ascii("\x7f") is True
        assert is_ascii("\x80") is False


# ── _parse_from_filter() ─────────────────────────────────────


class TestParseFromFilter:
    """``_parse_from_filter``: split comma-separated filter into cleaned parts."""

    def test_single_email(self, env):
        server = env["ir.mail_server"].browse()
        result = server._parse_from_filter("user@example.com")
        assert result == ["user@example.com"]

    def test_multiple_entries(self, env):
        server = env["ir.mail_server"].browse()
        result = server._parse_from_filter("user@example.com, example.org")
        assert result == ["user@example.com", "example.org"]

    def test_strips_whitespace(self, env):
        server = env["ir.mail_server"].browse()
        result = server._parse_from_filter("  a@b.com ,  c.org  ")
        assert result == ["a@b.com", "c.org"]

    def test_empty_string(self, env):
        server = env["ir.mail_server"].browse()
        assert server._parse_from_filter("") == []

    def test_false_input(self, env):
        server = env["ir.mail_server"].browse()
        assert server._parse_from_filter(False) == []

    def test_skips_empty_parts(self, env):
        """Consecutive commas produce empty parts that are filtered out."""
        server = env["ir.mail_server"].browse()
        result = server._parse_from_filter("a@b.com,,c@d.com")
        assert result == ["a@b.com", "c@d.com"]


# ── _match_from_filter() ─────────────────────────────────────


class TestMatchFromFilter:
    """``_match_from_filter``: match email against filter (email or domain)."""

    def test_empty_filter_matches_all(self, env):
        """Falsy filter always matches."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter("any@example.com", False) is True
        assert server._match_from_filter("any@example.com", "") is True

    def test_exact_email_match(self, env):
        """Full email address in filter matches."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter(
            "user@example.com", "user@example.com"
        ) is True

    def test_email_case_insensitive(self, env):
        """Email matching is case-insensitive (normalized)."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter(
            "User@Example.COM", "user@example.com"
        ) is True

    def test_domain_match(self, env):
        """Domain-only filter matches any email at that domain."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter(
            "anyone@example.com", "example.com"
        ) is True

    def test_domain_no_match(self, env):
        """Different domain does not match."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter(
            "user@other.com", "example.com"
        ) is False

    def test_email_no_match(self, env):
        """Different email does not match email filter."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter(
            "alice@example.com", "bob@example.com"
        ) is False

    def test_multi_filter_email_match(self, env):
        """Comma-separated filter with matching email."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter(
            "user@example.com", "other@test.com, user@example.com"
        ) is True

    def test_multi_filter_domain_match(self, env):
        """Comma-separated filter with matching domain."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter(
            "anyone@mycompany.org", "example.com, mycompany.org"
        ) is True

    def test_multi_filter_no_match(self, env):
        """No entry in comma-separated filter matches."""
        server = env["ir.mail_server"].browse()
        assert server._match_from_filter(
            "user@unknown.com", "example.com, other@test.com"
        ) is False
