import unittest

from markupsafe import Markup

from odoo.libs.text.html import (
    create_link,
    html2plaintext,
    html_keep_url,
    html_normalize,
    html_sanitize,
    normalize_url,
    plaintext2html,
)


def sanitize(src: str) -> str:
    out = html_sanitize(src)
    assert out is not None, f"html_sanitize returned None for {src!r}"
    return out


class TestHtmlNormalizeEncodingStrip(unittest.TestCase):
    def test_strips_only_the_encoding_attribute(self):
        out = html_normalize('<p><span encoding="x" style="color:red">imp</span> t</p>')
        self.assertIn("imp", out)
        self.assertIn("t", out)
        self.assertIn("color:red", out)
        self.assertNotIn("encoding", out)

    def test_plain_content_unchanged(self):
        out = html_normalize("<p>hi <b>bold</b> there</p>")
        self.assertIn("bold", out)
        self.assertNotIn("encoding", out)


class TestSanitizeSvgLink(unittest.TestCase):
    def test_javascript_scheme_is_stripped(self):
        out = sanitize(
            '<svg><a xlink:href="javascript:alert(1)"><text>x</text></a></svg>'
        )
        self.assertNotIn("javascript:", out)

    def test_data_scheme_is_stripped(self):
        out = sanitize(
            '<svg><a xlink:href="data:text/html;base64,PHNjcmlwdD4="><text>x</text></a></svg>'
        )
        self.assertNotIn("base64", out)

    def test_http_url_survives(self):
        out = sanitize(
            '<svg><a xlink:href="https://ok.example"><text>x</text></a></svg>'
        )
        self.assertIn("https://ok.example", out)


class TestCreateLink(unittest.TestCase):
    def test_url_cannot_break_out_of_href(self):
        out = create_link('https://x/"><script>alert(1)</script>', "lbl")
        self.assertNotIn('"><script>', out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIsInstance(out, Markup)

    def test_label_is_escaped(self):
        out = create_link("https://x", 'a "b" <c>')
        self.assertNotIn("<c>", out)
        self.assertIn("&lt;c&gt;", out)

    def test_legit_url_keeps_ampersand_escaped_in_href(self):
        out = create_link("http://e.com/a?b=1&c=2", "link")
        self.assertIn('href="http://e.com/a?b=1&amp;c=2"', out)

    def test_markup_input_is_not_double_escaped(self):
        out = create_link(Markup("http://e.com/x"), Markup("safe"))
        self.assertIn('href="http://e.com/x"', out)
        self.assertIn(">safe<", out)

    def test_javascript_scheme_is_rejected(self):
        out = create_link("javascript:alert(1)", "lbl")
        self.assertNotIn("javascript:", out)
        self.assertIn('href="#"', out)

    def test_data_scheme_is_rejected(self):
        out = create_link("data:text/html,<script>alert(1)</script>", "lbl")
        self.assertNotIn("data:", out)
        self.assertIn('href="#"', out)

    def test_mailto_and_tel_are_allowed(self):
        self.assertIn('href="mailto:a@b.com"', create_link("mailto:a@b.com", "x"))
        self.assertIn('href="tel:+123"', create_link("tel:+123", "x"))

    def test_scheme_less_relative_url_is_kept(self):
        out = create_link("/some/path", "lbl")
        self.assertIn('href="/some/path"', out)


class TestNormalizeUrl(unittest.TestCase):
    def test_protocol_relative_url_is_not_treated_as_local(self):
        out = normalize_url("//evil.com/x")
        self.assertNotEqual(out, "//evil.com/x")

    def test_single_slash_local_path_stays_local(self):
        self.assertEqual(normalize_url("/some/path"), "/some/path")

    def test_query_and_fragment_stay_as_is(self):
        self.assertEqual(normalize_url("?a=1"), "?a=1")
        self.assertEqual(normalize_url("#frag"), "#frag")

    def test_bare_host_gets_http_prefix(self):
        self.assertEqual(normalize_url("example.com"), "http://example.com")


class TestHtmlKeepUrl(unittest.TestCase):
    def test_no_double_escaping(self):
        out = html_keep_url("see http://e.com/a?b=1&c=2 now")
        self.assertIn("&amp;c=2", out)
        self.assertNotIn("&amp;amp;", out)


class TestPlaintext2Html(unittest.TestCase):
    def test_container_tag_with_attributes_rejected(self):
        with self.assertRaises(ValueError):
            plaintext2html("hi", container_tag='div onclick="evil()"')

    def test_container_tag_with_angle_bracket_rejected(self):
        with self.assertRaises(ValueError):
            plaintext2html("hi", container_tag="div><script")

    def test_simple_container_tag_allowed(self):
        out = str(plaintext2html("hi", container_tag="section"))
        self.assertTrue(out.startswith("<section>"))
        self.assertTrue(out.endswith("</section>"))


class TestHtml2Plaintext(unittest.TestCase):
    DOC = (
        '<html><body><div id="content">HELLO</div>'
        '<div id="other">NO</div></body></html>'
    )

    def test_body_id_matches_only_target(self):
        out = html2plaintext(self.DOC, body_id="content")
        self.assertIn("HELLO", out)
        self.assertNotIn("NO", out)

    def test_body_id_injection_is_inert(self):
        out = html2plaintext(self.DOC, body_id='content"] | //*[@id="other')
        self.assertNotIn("NO", out)
        self.assertNotIn("HELLO", out)

    def test_body_id_miss_returns_empty(self):
        out = html2plaintext(self.DOC, body_id="does-not-exist")
        self.assertEqual(out.strip(), "")


class TestSanitizeRemovesActiveContent(unittest.TestCase):
    def test_script_element_is_removed(self):
        out = sanitize("<p>keep</p><script>alert(1)</script>")
        self.assertNotIn("script", out)
        self.assertIn("keep", out)

    def test_event_handler_attribute_is_removed(self):
        out = sanitize('<p onclick="alert(1)">keep</p>')
        self.assertNotIn("onclick", out)
        self.assertIn("keep", out)

    def test_javascript_url_in_href_is_stripped(self):
        out = sanitize('<a href="javascript:alert(1)">x</a>')
        self.assertNotIn("javascript:", out)

    def test_xml_base_is_stripped_regardless_of_sanitize_attributes(self):
        src = '<div xml:base="javascript:alert(1)"><p>keep</p></div>'
        for sanitize_attributes in (False, True):
            with self.subTest(sanitize_attributes=sanitize_attributes):
                out = html_sanitize(src, sanitize_attributes=sanitize_attributes)
                self.assertNotIn("xml:base", out)
                self.assertIn("keep", out)

    def test_ordinary_markup_survives(self):
        out = sanitize("<p><b>bold</b> and <i>italic</i></p>")
        self.assertIn("<b>bold</b>", out)
        self.assertIn("<i>italic</i>", out)


if __name__ == "__main__":
    unittest.main()


class TestSmallHtmlHelpers(unittest.TestCase):
    def test_a_non_web_scheme_is_kept_as_written(self):
        for url in ("mailto:a@b.com", "tel:+3212345", "sms:+3212345"):
            with self.subTest(url=url):
                self.assertEqual(normalize_url(url), url)
        self.assertEqual(normalize_url("example.com"), "http://example.com")
        self.assertEqual(normalize_url("localhost:8069"), "http://localhost:8069")

    def test_prepend_finds_an_uppercase_body(self):
        from odoo.libs.text.html import prepend_html_content

        self.assertEqual(
            prepend_html_content("<HTML><BODY><p>b</p></BODY></HTML>", "<p>c</p>"),
            "<HTML><BODY><p>c</p><p>b</p></BODY></HTML>",
        )
