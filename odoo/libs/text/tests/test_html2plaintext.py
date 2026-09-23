import unittest

from odoo.libs.text.html import html2plaintext


class TestElementlessInput(unittest.TestCase):
    def test_comment_only(self):
        self.assertEqual(html2plaintext("<!-- just a comment -->"), "")

    def test_doctype_only(self):
        self.assertEqual(html2plaintext("<!DOCTYPE html>"), "")

    def test_processing_instruction_only(self):
        self.assertEqual(html2plaintext("<?xml version='1.0'?>"), "")

    def test_comment_only_with_body_id(self):
        self.assertEqual(html2plaintext("<!-- x -->", body_id="content"), "")


class TestFalsyInput(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(html2plaintext(""), "")

    def test_none(self):
        self.assertEqual(html2plaintext(None), "")

    def test_whitespace(self):
        self.assertEqual(html2plaintext("   \n  "), "")


class TestStillConvertsRealContent(unittest.TestCase):
    def test_bare_text(self):
        self.assertEqual(html2plaintext("hello"), "hello")

    def test_paragraphs(self):
        self.assertEqual(html2plaintext("<p>one</p><p>two</p>"), "one\ntwo")

    def test_comment_followed_by_content(self):
        self.assertEqual(html2plaintext("<!-- c --><p>kept</p>"), "kept")

    def test_link_reference_is_appended(self):
        self.assertIn(
            "https://example.com",
            html2plaintext('<a href="https://example.com">site</a>'),
        )

    def test_body_id_miss_returns_empty(self):
        self.assertEqual(html2plaintext("<p>secret</p>", body_id="absent"), "")

    def test_body_id_hit(self):
        self.assertEqual(
            html2plaintext('<div id="c">wanted</div><p>other</p>', body_id="c"),
            "wanted",
        )


if __name__ == "__main__":
    unittest.main()


class TestNonTextContent(unittest.TestCase):
    def test_a_str_carrying_an_xml_encoding_declaration_parses(self):
        self.assertEqual(
            html2plaintext(
                '<?xml version="1.0" encoding="utf-8"?><html><body><p>hi</p></body></html>'
            ),
            "hi",
        )

    def test_style_and_script_bodies_are_not_text(self):
        self.assertEqual(
            html2plaintext(
                "<body><style>p{color:red}</style><p>Hello</p>"
                "<script>var a=1;</script></body>"
            ),
            "Hello",
        )

    def test_a_comment_holding_a_bracket_is_dropped_whole(self):
        self.assertEqual(html2plaintext("<p>a <!-- a > b --> c</p>"), "a c")

    def test_non_ascii_text_survives_the_byte_parse(self):
        self.assertEqual(html2plaintext("<p>café \U0001f600</p>"), "café \U0001f600")


class TestLoneSurrogate(unittest.TestCase):
    def test_a_lone_surrogate_does_not_raise(self):
        self.assertIn("x", html2plaintext("a\ud800b<p>x</p>"))
