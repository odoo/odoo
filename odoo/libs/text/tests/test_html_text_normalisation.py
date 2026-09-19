import unittest

from lxml import etree
from lxml import html as lxml_html
from markupsafe import Markup

from odoo.libs.text.html import (
    add_html_content,
    fromstring,
    html2plaintext,
    html_normalize,
    html_sanitize,
    html_to_inner_content,
    prepend_html_content,
)


class TestHtml2PlaintextEntities(unittest.TestCase):
    def test_literal_entity_text_survives(self):
        self.assertEqual(
            html2plaintext("<p>use &amp;nbsp; for a space</p>"),
            "use &nbsp; for a space",
        )

    def test_literal_entity_alone_is_not_swallowed(self):
        self.assertEqual(html2plaintext("<p>&amp;nbsp;</p>"), "&nbsp;")

    def test_a_real_non_breaking_space_is_still_a_non_breaking_space(self):
        self.assertEqual(html2plaintext("<p>a&nbsp;b</p>"), "a\N{NO-BREAK SPACE}b")

    def test_the_three_reachable_entities_still_decode(self):
        self.assertEqual(html2plaintext("<p>&amp;lt; &lt; &gt;</p>"), "&lt; < >")


class TestHtml2PlaintextKeepsStructure(unittest.TestCase):
    def test_a_break_between_blocks_still_makes_a_blank_line(self):
        self.assertEqual(
            html2plaintext("<h2>A</h2>\n<br/>\n<h3>B</h3>"), "**A**\n\n*B*"
        )

    def test_adjacent_blocks_stay_one_line_apart(self):
        self.assertEqual(html2plaintext("<p>one</p><p>two</p>"), "one\ntwo")

    def test_html_to_inner_content_collapses_because_it_has_no_structure(self):
        self.assertEqual(html_to_inner_content("<p>a    b</p>"), "a b")
        self.assertEqual(html_to_inner_content("<p>a</p><br><br><p>b</p>"), "a b")


class TestAppendContentToHtml(unittest.TestCase):
    def test_caller_markup_is_left_alone(self):
        result = add_html_content('<HTML><BODY><A HREF="/x">Hi</A></BODY></HTML>', "x")
        self.assertIn('<A HREF="/x">Hi</A>', result)
        self.assertIn("</BODY>", result)

    def test_closing_tag_with_whitespace_is_found(self):
        result = add_html_content("<html><body>x</body >", "content")
        self.assertTrue(result.endswith("</body >"), result)

    def test_falls_back_to_html_then_to_the_end(self):
        self.assertTrue(add_html_content("<html>x</html>", "c").endswith("</html>"))
        self.assertEqual(
            add_html_content("<div>x</div>", "c"), "<div>x</div>\n<p>c</p>\n"
        )

    def test_uppercase_and_lowercase_insert_at_the_same_place(self):
        lower = add_html_content("<html><body>x</body></html>", "c")
        upper = add_html_content("<HTML><BODY>x</BODY></HTML>", "c")
        self.assertEqual(lower.lower(), upper.lower())


class TestPrependHtmlContent(unittest.TestCase):
    def test_returns_str_and_does_not_over_mark_an_untrusted_body(self):
        result = prepend_html_content("<body>5 < 6</body>", Markup("<p>c</p>"))
        self.assertIsInstance(result, str)
        self.assertNotIsInstance(result, Markup)
        self.assertEqual(result, "<body><p>c</p>5 < 6</body>")

    def test_a_markup_body_stays_markup_and_escapes_untrusted_content(self):
        body = Markup("<body><p>b</p></body>")
        trusted = prepend_html_content(body, Markup("<p>c</p>"))
        self.assertIsInstance(trusted, Markup)
        self.assertEqual(trusted, "<body><p>c</p><p>b</p></body>")
        untrusted = prepend_html_content(body, "<p>c</p>")
        self.assertIsInstance(untrusted, Markup)
        self.assertEqual(untrusted, "<body>&lt;p&gt;c&lt;/p&gt;<p>b</p></body>")

    def test_content_is_inserted_after_the_body_tag(self):
        self.assertEqual(
            prepend_html_content("<body><p>b</p></body>", "<p>c</p>"),
            "<body><p>c</p><p>b</p></body>",
        )


class TestFromstringReturnsATreeTypedElement(unittest.TestCase):
    INPUTS = [
        "Many2one<string>",
        "plain text",
        "<p>a</p>",
        "a<b>c</b>",
        "<div>x</div><div>y</div>",
        "<body>a</body><body>b</body>",
        "<html><head><title>t</title></head><body>x</body></html>",
        "text<span>s</span>more",
        "<table><tr><td>c</td></tr></table>",
        "<!-- c -->x",
    ]

    def test_the_two_classes_really_do_differ(self):
        self.assertFalse(hasattr(etree.Element("p"), "rewrite_links"))
        self.assertTrue(hasattr(lxml_html.fromstring("<p>x</p>"), "rewrite_links"))

    def test_every_shape_comes_back_as_an_html_element(self):
        for source in self.INPUTS:
            with self.subTest(source=source):
                doc, _single = fromstring(source)
                self.assertIsInstance(doc, lxml_html.HtmlElement)
                self.assertTrue(hasattr(doc, "rewrite_links"))

    def test_the_class_does_not_depend_on_a_live_reference(self):
        first = type(fromstring("Many2one<string>")[0])
        second = type(fromstring("Many2one<string>")[0])
        self.assertIs(first, second)
        self.assertIs(first, lxml_html.HtmlElement)

    def test_sanitize_survives_an_input_that_produced_a_bare_element(self):
        self.assertEqual(str(html_sanitize("Many2one<string>")), "<p>Many2one</p>")

    def test_non_ascii_inside_a_comment_survives(self):
        self.assertEqual(
            html_normalize("<p>Bonjour</p><!-- Résumé du café --><p>Adiós</p>"),
            "<p>Bonjour</p><!-- Résumé du café --><p>Adiós</p>",
        )

    def test_non_ascii_inside_a_comment_survives_sanitization(self):
        self.assertEqual(
            str(html_sanitize("<p>Hi</p><!-- Résumé -->")), "<p>Hi</p><!-- Résumé -->"
        )

    def test_non_ascii_in_text_was_never_the_problem(self):
        self.assertEqual(html_normalize("<p>Adiós</p>"), "<p>Adiós</p>")


if __name__ == "__main__":
    unittest.main()
