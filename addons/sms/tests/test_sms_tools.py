from odoo.tests import BaseCase, tagged

from odoo.addons.sms.tools.sms_tools import sms_content_to_rendered_html


@tagged("post_install", "-at_install")
class TestSmsContentToRenderedHtml(BaseCase):
    """A URL containing a character HTML-escaping changes (`&`, `<`, `>`)
    must still be linkified, not silently left as escaped plain text.
    """

    def test_url_with_ampersand_is_linkified(self):
        result = sms_content_to_rendered_html(
            "Check this out: https://example.com/path?a=1&b=2 thanks"
        )
        self.assertIn(
            '<a href="https://example.com/path?a=1&amp;b=2"',
            result,
            "a URL whose query string contains '&' must still become a link",
        )

    def test_url_without_special_characters_is_linkified(self):
        result = sms_content_to_rendered_html(
            "Check this out: https://example.com/path?a=1 thanks"
        )
        self.assertIn('<a href="https://example.com/path?a=1"', result)

    def test_surrounding_text_stays_escaped(self):
        result = sms_content_to_rendered_html(
            "<script>alert(1)</script> https://example.com/x?y=<z>&w=2 done"
        )
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", result)
        self.assertNotIn("<script>", result)

    def test_newlines_are_preserved_as_br(self):
        result = sms_content_to_rendered_html("line1\nline2\rline3")
        self.assertEqual(result, "line1<br/>line2<br/>line3")
