import unittest

from odoo.libs.email.parsing import formataddr


class TestFormataddr(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            formataddr(("John Doe", "john@example.com")),
            '"John Doe" <john@example.com>',
        )

    def test_address_only(self):
        self.assertEqual(formataddr(("", "john@example.com")), "john@example.com")

    def test_strips_crlf_from_name(self):
        out = formataddr(("Foo\r\nBcc: attacker@evil.com", "user@example.com"))
        self.assertNotIn("\r", out)
        self.assertNotIn("\n", out)

    def test_strips_control_chars_from_address(self):
        out = formataddr(("Name", "user\r\n@example.com"))
        self.assertNotIn("\r", out)
        self.assertNotIn("\n", out)


if __name__ == "__main__":
    unittest.main()


def test_an_uppercase_international_domain_is_encoded_not_refused():
    from odoo.libs.email.parsing import extract_rfc2822_addresses, formataddr

    assert formataddr(("", "x@EXÄMPLE.com"), "ascii") == "x@xn--exmple-cua.com"
    assert extract_rfc2822_addresses("x@EXÄMPLE.com") == ["x@xn--exmple-cua.com"]


def test_an_empty_address_is_refused_not_rendered_as_an_at_sign():
    import pytest

    from odoo.libs.email.parsing import formataddr

    for pair in (("x", ""), ("", "")):
        with pytest.raises(ValueError, match="required"):
            formataddr(pair)
