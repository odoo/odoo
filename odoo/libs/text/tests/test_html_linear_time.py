import time
import unittest

from odoo.libs.text.html import html_keep_url, html_normalize, html_sanitize

_BUDGET = 1.0


class TestLinearTime(unittest.TestCase):
    def assert_fast(self, fn, src):
        start = time.perf_counter()
        fn(src)
        self.assertLess(time.perf_counter() - start, _BUDGET)

    def test_unclosed_tags_before_an_encoding_attribute(self):
        self.assert_fast(html_normalize, "<a " * 20000)

    def test_unclosed_office_tags(self):
        self.assert_fast(html_normalize, "<o:" * 20000)

    def test_many_siblings_after_a_quote_marker(self):
        self.assert_fast(
            html_normalize,
            '<div><div class="gmail_extra">q</div>' + "<p>x</p>" * 8000 + "</div>",
        )

    def test_many_forward_sweeping_markers(self):
        self.assert_fast(
            html_normalize, "<div>" + '<hr id="stopSpelling">' * 8000 + "</div>"
        )

    def test_a_long_url_followed_by_a_quote(self):
        self.assert_fast(html_keep_url, "http://" + "a" * 80000 + '"')


class TestQuoteSweep(unittest.TestCase):
    def test_a_comment_after_a_forward_marker_does_not_lose_the_body(self):
        out = str(
            html_sanitize(
                '<div><p>reply</p><hr id="stopSpelling"><!-- c --><p>old</p></div>'
            )
        )
        self.assertNotIn("Unknown error", out)
        self.assertIn('<p data-o-mail-quote="1">old</p>', out)

    def test_every_sibling_after_the_first_marker_is_quoted(self):
        out = html_normalize(
            '<div><p>a</p><hr id="stopSpelling"><p>b</p>'
            '<hr id="stopSpelling"><p>c</p></div>'
        )
        self.assertIn("<p>a</p>", out)
        self.assertEqual(out.count('data-o-mail-quote="1"'), 4)

    def test_a_comment_between_quoted_siblings_keeps_the_chain(self):
        out = html_normalize(
            '<div><div class="gmail_extra">q</div><!-- c --><p>x</p></div>'
        )
        self.assertIn('<p data-o-mail-quote="1">x</p>', out)
