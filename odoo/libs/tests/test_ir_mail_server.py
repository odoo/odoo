"""Unit tests for odoo.libs.ir_mail_server — no Odoo ORM dependency."""

import email.policy
import unittest

from odoo.libs.ir_mail_server import (
    RFC5322_IDENTIFICATION_HEADERS,
    IdentificationFieldsNoFoldPolicy,
    make_no_fold_smtp_policy,
)


class TestRFC5322IdentificationHeaders(unittest.TestCase):
    """Test RFC5322_IDENTIFICATION_HEADERS constant."""

    def test_is_frozenset(self):
        self.assertIsInstance(RFC5322_IDENTIFICATION_HEADERS, frozenset)

    def test_contains_message_id(self):
        self.assertIn("message-id", RFC5322_IDENTIFICATION_HEADERS)

    def test_contains_in_reply_to(self):
        self.assertIn("in-reply-to", RFC5322_IDENTIFICATION_HEADERS)

    def test_contains_references(self):
        self.assertIn("references", RFC5322_IDENTIFICATION_HEADERS)

    def test_contains_resent_msg_id(self):
        self.assertIn("resent-msg-id", RFC5322_IDENTIFICATION_HEADERS)

    def test_all_lowercase(self):
        for header in RFC5322_IDENTIFICATION_HEADERS:
            self.assertEqual(header, header.lower())

    def test_length(self):
        self.assertEqual(len(RFC5322_IDENTIFICATION_HEADERS), 4)


class TestIdentificationFieldsNoFoldPolicy(unittest.TestCase):
    """Test IdentificationFieldsNoFoldPolicy class."""

    def test_is_email_policy_subclass(self):
        self.assertTrue(
            issubclass(IdentificationFieldsNoFoldPolicy, email.policy.EmailPolicy)
        )

    def test_fold_non_identification_header(self):
        """Non-identification headers should fold normally."""
        policy = make_no_fold_smtp_policy()
        # Subject header should still fold (uses default behavior)
        result = policy._fold("Subject", "A normal subject line", refold_binary=True)
        self.assertIn("Subject", result)

    def test_fold_message_id_header(self):
        """Message-Id should not be folded (no line wrapping)."""
        policy = make_no_fold_smtp_policy()
        long_msgid = "<very-long-message-id-that-would-normally-be-folded@example.com>"
        result = policy._fold("Message-Id", long_msgid, refold_binary=True)
        self.assertIn(long_msgid, result)


class TestMakeNoFoldSmtpPolicy(unittest.TestCase):
    """Test make_no_fold_smtp_policy factory function."""

    def test_returns_correct_type(self):
        policy = make_no_fold_smtp_policy()
        self.assertIsInstance(policy, IdentificationFieldsNoFoldPolicy)

    def test_preserves_smtp_linesep(self):
        policy = make_no_fold_smtp_policy()
        self.assertEqual(policy.linesep, email.policy.SMTP.linesep)


if __name__ == "__main__":
    unittest.main()
