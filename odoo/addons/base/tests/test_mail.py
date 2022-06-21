# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from unittest.mock import patch

import email.policy
import email.message
import re
import threading

from odoo.addons.base.models.ir_mail_server import extract_rfc2822_addresses
from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.tests import tagged
from odoo.fields import Html
from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import (
    is_html_empty, html_to_inner_content, html_sanitize, append_content_to_html, plaintext2html,
    email_split, email_domain_normalize,
    misc, formataddr,
    prepend_html_content,
    quote_email,
)

from . import test_mail_examples


@tagged('mail_sanitize')
class TestSanitizer(BaseCase):
    """ Test the html sanitizer that filters html to remove unwanted attributes """

    def test_basic_sanitizer(self):
        cases = [
            ("yop", "<p>yop</p>"),  # simple
            ("<p>yop", "<p>yop</p>"),  # unclosed tag
            ("lala<p>yop</p>xxx", "lala<p>yop</p>xxx"),
            ("Merci à l'intérêt pour notre produit.nous vous contacterons bientôt. Merci",
             "<p>Merci à l'intérêt pour notre produit.nous vous contacterons bientôt. Merci</p>"),  # unicode
            ("<p>yop", "<p>yop</p>"),
        ]
        for content, expected in cases:
            html = html_sanitize(content)
            self.assertEqual(html, expected, 'html_sanitize is broken')

    def test_evil_malicious_code(self):
        # taken from https://www.owasp.org/index.php/XSS_Filter_Evasion_Cheat_Sheet#Tests
        cases = [
            ("<IMG SRC=javascript:alert('XSS')>"),  # no quotes and semicolons
            ("<IMG SRC=&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;&#97;&#108;&#101;&#114;&#116;&#40;&#39;&#88;&#83;&#83;&#39;&#41;>"),  # UTF-8 Unicode encoding
            ("<IMG SRC=&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29>"),  # hex encoding
            ("<IMG SRC=\"jav&#x0D;ascript:alert('XSS');\">"),  # embedded carriage return
            ("<IMG SRC=\"jav&#x0A;ascript:alert('XSS');\">"),  # embedded newline
            ("<IMG SRC=\"jav   ascript:alert('XSS');\">"),  # embedded tab
            ("<IMG SRC=\"jav&#x09;ascript:alert('XSS');\">"),  # embedded encoded tab
            ("<IMG SRC=\" &#14;  javascript:alert('XSS');\">"),  # spaces and meta-characters
            ("<IMG SRC=\"javascript:alert('XSS')\""),  # half-open html
            ("<IMG \"\"\"><SCRIPT>alert(\"XSS\")</SCRIPT>\">"),  # malformed tag
            ("<SCRIPT/XSS SRC=\"http://ha.ckers.org/xss.js\"></SCRIPT>"),  # non-alpha-non-digits
            ("<SCRIPT/SRC=\"http://ha.ckers.org/xss.js\"></SCRIPT>"),  # non-alpha-non-digits
            ("<<SCRIPT>alert(\"XSS\");//<</SCRIPT>"),  # extraneous open brackets
            ("<SCRIPT SRC=http://ha.ckers.org/xss.js?< B >"),  # non-closing script tags
            ("<INPUT TYPE=\"IMAGE\" SRC=\"javascript:alert('XSS');\">"),  # input image
            ("<IMG DYNSRC=\"javascript:alert('XSS')\">"),  # img dynsrc
            ("<IMG LOWSRC=\"javascript:alert('XSS')\">"),  # img lowsrc
            ("<TABLE BACKGROUND=\"javascript:alert('XSS')\">"),  # table
            ("<IMG SRC='vbscript:msgbox(\"XSS\")'>"),  # VBscrip in an image
            ("<BODY ONLOAD=alert('XSS')>"),  # event handler
            ("<BR SIZE=\"&{alert('XSS')}\>"),  # & javascript includes
            ("<LINK REL=\"stylesheet\" HREF=\"javascript:alert('XSS');\">"),  # style sheet
            ("<LINK REL=\"stylesheet\" HREF=\"http://ha.ckers.org/xss.css\">"),  # remote style sheet
            ("<STYLE>@import'http://ha.ckers.org/xss.css';</STYLE>"),  # remote style sheet 2
            ("<META HTTP-EQUIV=\"Link\" Content=\"<http://ha.ckers.org/xss.css>; REL=stylesheet\">"),  # remote style sheet 3
            ("<IMG STYLE=\"xss:expr/*XSS*/ession(alert('XSS'))\">"),  # style attribute using a comment to break up expression
            ("<a href='javascript://test'> click </a>"),
            ("<a href='javascript:/test'> click </a>"),
            ("<a href='javascript:test'> click </a>"),
            ("<a href='   javascript:test   '> click </a>"),
        ]
        for content in cases:
            html = html_sanitize(content)
            self.assertNotIn('javascript', html, 'html_sanitize did not remove a malicious javascript')
            self.assertTrue('ha.ckers.org' not in html or 'http://ha.ckers.org/xss.css' in html, 'html_sanitize did not remove a malicious code in %s (%s)' % (content, html))

        content = "<!--[if gte IE 4]><SCRIPT>alert('XSS');</SCRIPT><![endif]-->"  # down-level hidden block
        self.assertEqual(html_sanitize(content, silent=False), '')

        cases = [
            # Abuse JS / CSS / Attribute parsers
            ("<div title='</div>'>test", """<div title="&lt;/div>">test</div>"""),
            ("<div style='/*'> <p title='*/ onclick=alert(1)'/>", '<div style=""> <p title="*/ onclick=alert(1)"></p></div>'),
            ("<noscript> <p title='</noscript> <div onclick=alert(1)>'/>", "<div>'/&gt;</div>"),
            ("<style>test {} </style>", ""),
            # XSS via data URI
            ('<a href="data:text/html;base64,PHNjcmlwdD5hbGVydCgiSGVsbG8iKTs8L3NjcmlwdD4="> click me </a>', '<a> click me </a>')
        ]

        for content, expected in cases:
            html = html_sanitize(content, sanitize_style=True, sanitize_tags=True)
            self.assertEqual(html, expected)

    def test_html(self):
        sanitized_html = html_sanitize(test_mail_examples.MISC_HTML_SOURCE)
        for tag in ['<div', '<b', '<i', '<u', '<strike', '<li', '<blockquote', '<a href']:
            self.assertIn(tag, sanitized_html, 'html_sanitize stripped too much of original html')
        for attr in ['javascript']:
            self.assertNotIn(attr, sanitized_html, 'html_sanitize did not remove enough unwanted attributes')

    def test_sanitize_unescape_emails(self):
        not_emails = [
            '<blockquote cite="mid:CAEJSRZvWvud8c6Qp=wfNG6O1+wK3i_jb33qVrF7XyrgPNjnyUA@mail.gmail.com" type="cite">cat</blockquote>',
            '<img alt="@github-login" class="avatar" height="36" src="/web/image/pi" width="36">']
        for not_email in not_emails:
            sanitized = html_sanitize(not_email)
            left_part = not_email.split('>')[0]  # take only left part, as the sanitizer could add data information on node
            self.assertNotIn(misc.html_escape(not_email), sanitized, 'html_sanitize stripped emails of original html')
            self.assertIn(left_part, sanitized)

    def test_style_parsing(self):
        tests = [
            (
                '<span style="position: fixed; top: 0px; left: 50px; width: 40%; height: 50%; background-color: red;">Coin coin </span>',
                ['background-color: red', 'Coin coin'],
                ['position', 'top', 'left'],
            ),
            (
                """
                    <div style='before: "Email Address coincoin cheval lapin";
                        font-size: 30px; max-width: 100%; after: "Not sure

                          this means anything"
                    ; some-property: 2px; top: 3'>youplaboum</div>
                """,
                ['font-size: 30px', 'youplaboum'],
                ['some-property', 'top', 'cheval'],
            ),
            (
                '<span style="width">Coincoin</span>',
                [],
                ['width'],
            )
        ]

        for test, in_lst, out_lst in tests:
            new_html = html_sanitize(test, sanitize_style=True)
            for text in in_lst:
                self.assertIn(text, new_html)
            for text in out_lst:
                self.assertNotIn(text, new_html)

        # style should not be sanitized if removed
        new_html = html_sanitize(tests[0][0], restricted_attributes=False, strip_style=True, strip_classes=False)
        self.assertEqual(new_html, '<span>Coin coin </span>')

    def test_style_class(self):
        html = html_sanitize(test_mail_examples.REMOVE_CLASS, restricted_attributes=True, sanitize_style=True, strip_classes=True)
        for ext in test_mail_examples.REMOVE_CLASS_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.REMOVE_CLASS_OUT:
            self.assertNotIn(ext, html,)

    def test_basic_style_with_default_html_field_config(self):
        html = html_sanitize(test_mail_examples.BASIC_STYLES,
                             sanitize_tags=Html.sanitize_tags,
                             restricted_attributes=Html.restricted_attributes,
                             sanitize_style=Html.sanitize_style,
                             sanitize_form=Html.sanitize_form,
                             strip_style=Html.strip_style,
                             strip_classes=Html.strip_classes)
        for expected_style in test_mail_examples.BASIC_STYLES_EXPECTED:
            self.assertIn(expected_style, html)

    def test_style_class_only(self):
        html = html_sanitize(test_mail_examples.REMOVE_CLASS, restricted_attributes=False, sanitize_style=True, strip_classes=True)
        for ext in test_mail_examples.REMOVE_CLASS_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.REMOVE_CLASS_OUT:
            self.assertNotIn(ext, html,)

    def test_edi_source(self):
        html = html_sanitize(test_mail_examples.EDI_LIKE_HTML_SOURCE)
        self.assertIn(
            'font-family: \'Lucida Grande\', Ubuntu, Arial, Verdana, sans-serif;', html,
            'html_sanitize removed valid styling')
        self.assertIn(
            'src="https://www.paypal.com/en_US/i/btn/btn_paynowCC_LG.gif"', html,
            'html_sanitize removed valid img')
        self.assertNotIn('</body></html>', html, 'html_sanitize did not remove extra closing tags')

    def test_quote_escape(self):
        """Test that the email quoting do not escape some specials characters."""
        src = 'éàè@$€£%~#'
        self.assertIn(src, quote_email(src))

    def test_quote_blockquote(self):
        html = quote_email(test_mail_examples.QUOTE_BLOCKQUOTE)
        for ext in test_mail_examples.QUOTE_BLOCKQUOTE_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.QUOTE_BLOCKQUOTE_OUT:
            self.assertIn('<span data-o-mail-quote="1">%s' % misc.html_escape(ext), html)

    def test_quote_thunderbird(self):
        html = quote_email(test_mail_examples.QUOTE_THUNDERBIRD_1)
        for ext in test_mail_examples.QUOTE_THUNDERBIRD_1_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.QUOTE_THUNDERBIRD_1_OUT:
            self.assertIn('<span data-o-mail-quote="1">%s</span>' % misc.html_escape(ext), html)

    def test_quote_hotmail_html(self):
        html = quote_email(test_mail_examples.QUOTE_HOTMAIL_HTML)
        for ext in test_mail_examples.QUOTE_HOTMAIL_HTML_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.QUOTE_HOTMAIL_HTML_OUT:
            self.assertIn(ext, html)

        html = quote_email(test_mail_examples.HOTMAIL_1)
        for ext in test_mail_examples.HOTMAIL_1_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.HOTMAIL_1_OUT:
            self.assertIn(ext, html)

    def test_quote_outlook_html(self):
        html = quote_email(test_mail_examples.QUOTE_OUTLOOK_HTML)
        for ext in test_mail_examples.QUOTE_OUTLOOK_HTML_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.QUOTE_OUTLOOK_HTML_OUT:
            self.assertIn(ext, html)

    def test_quote_thunderbird_html(self):
        html = quote_email(test_mail_examples.QUOTE_THUNDERBIRD_HTML)
        for ext in test_mail_examples.QUOTE_THUNDERBIRD_HTML_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.QUOTE_THUNDERBIRD_HTML_OUT:
            self.assertIn(ext, html)

    def test_quote_yahoo_html(self):
        html = quote_email(test_mail_examples.QUOTE_YAHOO_HTML)
        for ext in test_mail_examples.QUOTE_YAHOO_HTML_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.QUOTE_YAHOO_HTML_OUT:
            self.assertIn(ext, html)

    def test_quote_basic_text(self):
        test_data = [
            (
                """This is Sparta!\n--\nAdministrator\n+9988776655""",
                ['This is Sparta!'],
                ['\n--\nAdministrator\n+9988776655']
            ), (
                """<p>This is Sparta!\n--\nAdministrator</p>""",
                [],
                ['\n--\nAdministrator']
            ), (
                """<p>This is Sparta!<br/>--<br>Administrator</p>""",
                ['This is Sparta!'],
                []
            ), (
                """This is Sparta!\n>Ah bon ?\nCertes\n> Chouette !\nClair""",
                ['This is Sparta!', 'Certes', 'Clair'],
                ['\n>Ah bon ?', '\n> Chouette !']
            )
        ]
        for test, in_lst, out_lst in test_data:
            new_html = quote_email(test)
            for text in in_lst:
                self.assertIn(text, new_html)
            for text in out_lst:
                self.assertIn('<span data-o-mail-quote="1">%s</span>' % misc.html_escape(text), new_html)

    def test_quote_signature(self):
        test_data = [
            (
                """<div>Hello<pre>--<br />Administrator</pre></div>""",
                ["<pre data-o-mail-quote=\"1\">--", '<br data-o-mail-quote="1">'],
            )
        ]
        for test, in_lst in test_data:
            new_html = quote_email(test)
            for text in in_lst:
                self.assertIn(text, new_html)

    def test_quote_gmail(self):
        html = quote_email(test_mail_examples.GMAIL_1)
        for ext in test_mail_examples.GMAIL_1_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.GMAIL_1_OUT:
            self.assertIn('<span data-o-mail-quote="1">%s</span>' % misc.html_escape(ext), html)

    def test_quote_text(self):
        html = quote_email(test_mail_examples.TEXT_1)
        for ext in test_mail_examples.TEXT_1_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.TEXT_1_OUT:
            self.assertIn('<span data-o-mail-quote="1">%s</span>' % misc.html_escape(ext), html)

        html = quote_email(test_mail_examples.TEXT_2)
        for ext in test_mail_examples.TEXT_2_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.TEXT_2_OUT:
            self.assertIn('<span data-o-mail-quote="1">%s</span>' % misc.html_escape(ext), html)

    def test_quote_bugs(self):
        html = quote_email(test_mail_examples.BUG1)
        for ext in test_mail_examples.BUG_1_IN:
            self.assertIn(ext, html)
        for ext in test_mail_examples.BUG_1_OUT:
            self.assertIn('<span data-o-mail-quote="1">%s</span>' % misc.html_escape(ext), html)

    def test_misc(self):
        # False / void should not crash
        html = html_sanitize('')
        self.assertEqual(html, '')
        html = html_sanitize(False)
        self.assertEqual(html, False)

        # Message with xml and doctype tags don't crash
        html = html_sanitize(u'<?xml version="1.0" encoding="iso-8859-1"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n <head>\n  <title>404 - Not Found</title>\n </head>\n <body>\n  <h1>404 - Not Found</h1>\n </body>\n</html>\n')
        self.assertNotIn('encoding', html)
        self.assertNotIn('<title>404 - Not Found</title>', html)
        self.assertIn('<h1>404 - Not Found</h1>', html)

        src = '<p> test </p>\n<p> test </p>\n<p> test </p>'
        self.assertEqual(html_sanitize(src), src, 'Should have preserved the newlines')

        src = 'test <a>click me</a>'
        self.assertEqual(html_sanitize(src), '<p>%s</p>' % src)

        # Check that some special characters are not escaped
        src = 'éàè@$€£%~#'
        self.assertEqual(html_sanitize(src), '<p>%s</p>' % src)

        # sanitize_style=False
        self.assertEqual(html_sanitize("""<p style='"'>test</p>""", sanitize_style=False), """<p style='"'>test</p>""")
        self.assertEqual(html_sanitize("""<p style="'">test</p>""", sanitize_style=False), """<p style="'">test</p>""")
        self.assertEqual(html_sanitize("""<p style="\\"onclick=alert">test</p>""", sanitize_style=False), """<p style="\\">test</p>""")

        # inline image in base 64
        src = '<img src="data:image/jpeg;base64,aaaaaaa====" />'
        self.assertEqual(html_sanitize(src), src)

        # inline SVG not allowed
        src = '<img src="data:image/svg;base64,aaaaaaa====" />'
        self.assertEqual(html_sanitize(src), "<img />")

    def test_sanitize_with_cid(self):
        img_tag = '<img src="@" />'
        sanitized = html_sanitize(img_tag, strip_classes=True)
        self.assertEqual(img_tag, sanitized, "img with can have cid containing @ and shouldn't be escaped")

        src = '<img alt="Inline image 3" height="10" src="cid:ii_151b51a37e5eb7a6" width="10" />'
        sanitized = html_sanitize(src)
        self.assertIn('src', sanitized)
        self.assertEqual(src, sanitized)

    def test_sanitize_tags(self):
        sources = (
            ('<style>', ''),
            ('</style>', ''),
            ('<style/>', ''),
            ('< style >', '<p>&lt; style &gt;</p>'),
            ('<style onclick="alert(1)">', ''),
            ('<style> <style> test </style> </style> ', '  '),
            ('<p>&lt;style&gt;</p>', '<p>&lt;style&gt;</p>'),
            ('<sty<style>le/>', '<p>le/&gt;</p>'),  # try to trick the "KILLED_TAG"
            ('<sty&lt;style&gt;le/>', ''),
            ('<style unknown_attr=""> style {} </style>', ''),
            ('<style attr="bouh"> style {} </style> <p> test </p> <style/>', '<p> test </p>'),
            ('<style> <p> test </p> </style> bouh', '<p>bouh</p>'),
            ('<style unknown_attr=""> {} </style> <p> test </p> <style> style </style>', '<p> test </p>'),
            ('<__<killed>__>', '<p>&lt;____&gt;</p>'),  # Treat it as a normal unknown tag
            ('<__<kil<__<killed>__>led>__> <p> test </p> bouh', '&lt;____&gt;led&gt;__&gt; <p> test </p> bouh'),
        )
        for style, expected in sources:
            self.assertEqual(html_sanitize(style), expected)

        # Those elements will be sanitized with "sanitize_tags=False"
        sources = (
            (
                '<style unknown_attr="" onclick="alert(1)" title="ti"> style {} </style>',
                '<style title="ti"> style {} </style>',
            ), (
                '<style> style {before: "<test>"} </style>',
                '<style> style {before: "&lt;test&gt;"} </style>',
            ),
            ('<meta class="c" />', ''),
        )
        for source, expected in sources:
            self.assertEqual(
                html_sanitize(source, sanitize_tags=False),
                expected,
                'Should have kept the HTML tags but removed the unsafe attributes')

        # Test "sanitize_form=True"
        sources = (
            (
                "<form> </form> <style> style {} </style>",
                "<style> style {} </style>"
            ), (
                "<unknown_tag> test </unknown_tag> <form> </form>",
                "<unknown_tag> test </unknown_tag>",
            ), (
                "test <form> <input name='email'/> </form>",
                "<p>test</p>",
            ),
        )
        for html, expected in sources:
            self.assertEqual(
                html_sanitize(html, sanitize_tags=False, sanitize_form=True),
                expected,
                'Should have removed the form and kept other tags')

        # Test complex HTML elements on multiple lines
        multiline_html = """
            <style
            style="display: none;" type="text/css"
            data-o-mail-quote="1"
            >
            &amp;lt;!--
            p
                    {margin-top:0;
                    margin-bottom:0}
            --&amp;gt;
            </style>
            <p> text </p>
            <style
                style="display: none;"
                type="text/css"
                data-o-mail-quote="1"
            >
            &amp;lt;!--
            p
                    {margin-top:0;
                    margin-bottom:0}
            --&amp;gt;
            /* comment
            */
            </
            style
            >
        """
        self.assertEqual(html_sanitize(multiline_html), '<p> text </p>')

    def test_restricted_attributes(self):
        style = '<p unknown_attr="1" data-test-attribute="test" class="ok"> {} </p>'
        self.assertEqual(
            html_sanitize(style, restricted_attributes=True),
            '<p class="ok"> {} </p>',
            'Should have removed unknown attributes')

        self.assertEqual(
            html_sanitize(style, restricted_attributes=False),
            '<p class="ok" data-test-attribute="test"> {} </p>',
            'Should have removed unknown attributes but kept data attribute')

        style = '<p unknown_attr="1" data-invalid-attribute!!!="test" class="ok"> {} </p>'
        self.assertEqual(
            html_sanitize(style, restricted_attributes=False),
            '<p class="ok"> {} </p>',
            'The data attribute should be removed because it is invalid')

    def test_dangling_markup_injection(self):
        payloads = (
            """ <a title=' """,
            """ <a title=" """,
            """ <img src="http://attacker.com?a= """,
            """ <img src='http://attacker.com?a= """,
        )
        for payload in payloads:
            html = html_sanitize(
                payload,
                sanitize_tags=Html.sanitize_tags,
                restricted_attributes=False,
                sanitize_style=Html.sanitize_style,
                sanitize_form=Html.sanitize_form,
                strip_style=Html.strip_style,
                strip_classes=Html.strip_classes,
            )
            self.assertFalse(html.strip())

        payload = """ <a> <div> </a> </div> """
        html = html_sanitize(
            payload,
            sanitize_tags=Html.sanitize_tags,
            restricted_attributes=False,
            sanitize_style=Html.sanitize_style,
            sanitize_form=Html.sanitize_form,
            strip_style=Html.strip_style,
            strip_classes=Html.strip_classes,
        )
        self.assertEqual(html, "<a> </a><div><a> </a> </div>")

    # ms office is currently not supported, have to find a way to support it
    # def test_30_email_msoffice(self):
    #     new_html = html_sanitize(test_mail_examples.MSOFFICE_1, remove=True)
    #     for ext in test_mail_examples.MSOFFICE_1_IN:
    #         self.assertIn(ext, new_html)
    #     for ext in test_mail_examples.MSOFFICE_1_OUT:
    #         self.assertNotIn(ext, new_html)


@tagged('mail_sanitize')
class TestHtmlTools(BaseCase):
    """ Test some of our generic utility functions about html """

    def test_plaintext2html(self):
        cases = [
            ("First \nSecond \nThird\n \nParagraph\n\r--\nSignature paragraph", 'div',
             "<div><p>First <br/>Second <br/>Third</p><p>Paragraph</p><p>--<br/>Signature paragraph</p></div>"),
            ("First<p>It should be escaped</p>\nSignature", False,
             "<p>First&lt;p&gt;It should be escaped&lt;/p&gt;<br/>Signature</p>")
        ]
        for content, container_tag, expected in cases:
            html = plaintext2html(content, container_tag)
            self.assertEqual(html, expected, 'plaintext2html is broken')

    def test_html_html_to_inner_content(self):
        cases = [
            ('<div><p>First <br/>Second <br/>Third Paragraph</p><p>--<br/>Signature paragraph with a <a href="./link">link</a></p></div>',
             'First Second Third Paragraph -- Signature paragraph with a link'),
            ('<p>Now =&gt; processing&nbsp;entities&#8203;and extra whitespace too.  </p>',
             'Now =&gt; processing\u00A0entities\u200band extra whitespace too.'),
            ('<div>Look what happens with <p>unmatched tags</div>', 'Look what happens with unmatched tags'),
            ('<div>Look what happens with <p unclosed tags</div> Are we good?', 'Look what happens with Are we good?')
        ]
        for content, expected in cases:
            text = html_to_inner_content(content)
            self.assertEqual(text, expected, 'html_html_to_inner_content is broken')

    def test_append_to_html(self):
        test_samples = [
            ('<!DOCTYPE...><HTML encoding="blah">some <b>content</b></HtMl>', '--\nYours truly', True, True, False,
             '<!DOCTYPE...><html encoding="blah">some <b>content</b>\n<pre>--\nYours truly</pre>\n</html>'),
            ('<!DOCTYPE...><HTML encoding="blah">some <b>content</b></HtMl>', '--\nYours truly', True, False, False,
             '<!DOCTYPE...><html encoding="blah">some <b>content</b>\n<p>--<br/>Yours truly</p>\n</html>'),
            ('<html><body>some <b>content</b></body></html>', '--\nYours & <truly>', True, True, False,
             '<html><body>some <b>content</b>\n<pre>--\nYours &amp; &lt;truly&gt;</pre>\n</body></html>'),
            ('<html><body>some <b>content</b></body></html>', '<!DOCTYPE...>\n<html><body>\n<p>--</p>\n<p>Yours truly</p>\n</body>\n</html>', False, False, False,
             '<html><body>some <b>content</b>\n\n\n<p>--</p>\n<p>Yours truly</p>\n\n\n</body></html>'),
        ]
        for html, content, plaintext_flag, preserve_flag, container_tag, expected in test_samples:
            self.assertEqual(append_content_to_html(html, content, plaintext_flag, preserve_flag, container_tag), expected, 'append_content_to_html is broken')

    def test_is_html_empty(self):
        void_strings_samples = ['', False, ' ']
        for content in void_strings_samples:
            self.assertTrue(is_html_empty(content))

        void_html_samples = [
            '<p><br></p>', '<p><br> </p>', '<p><br /></p >',
            '<p style="margin: 4px"></p>',
            '<div style="margin: 4px"></div>',
            '<p class="oe_testing"><br></p>',
            '<p><span style="font-weight: bolder;"><font style="color: rgb(255, 0, 0);" class=" "></font></span><br></p>',
        ]
        for content in void_html_samples:
            self.assertTrue(is_html_empty(content), 'Failed with %s' % content)

        valid_html_samples = [
            '<p><br>1</p>', '<p>1<br > </p>', '<p style="margin: 4px">Hello World</p>',
            '<div style="margin: 4px"><p>Hello World</p></div>',
            '<p><span style="font-weight: bolder;"><font style="color: rgb(255, 0, 0);" class=" ">W</font></span><br></p>',
        ]
        for content in valid_html_samples:
            self.assertFalse(is_html_empty(content))

    def test_nl2br_enclose(self):
        """ Test formatting of nl2br when using Markup: consider new <br> tags
        as trusted without validating the whole input content. """
        source_all = [
            'coucou',
            '<p>coucou</p>',
            'coucou\ncoucou',
            'coucou\n\ncoucou',
            '<p>coucou\ncoucou\n\nzbouip</p>\n',
        ]
        expected_all = [
            Markup('<div>coucou</div>'),
            Markup('<div>&lt;p&gt;coucou&lt;/p&gt;</div>'),
            Markup('<div>coucou<br>\ncoucou</div>'),
            Markup('<div>coucou<br>\n<br>\ncoucou</div>'),
            Markup('<div>&lt;p&gt;coucou<br>\ncoucou<br>\n<br>\nzbouip&lt;/p&gt;<br>\n</div>'),
        ]
        for source, expected in zip(source_all, expected_all):
            with self.subTest(source=source, expected=expected):
                self.assertEqual(
                    nl2br_enclose(source, "div"),
                    expected,
                )

    def test_prepend_html_content(self):
        body = """
            <html>
                <body>
                    <div>test</div>
                </body>
            </html>
        """

        content = "<span>content</span>"

        result = prepend_html_content(body, content)
        result = re.sub(r'[\s\t]', '', result)
        self.assertEqual(result, "<html><body><span>content</span><div>test</div></body></html>")

        body = "<div>test</div>"
        content = "<span>content</span>"

        result = prepend_html_content(body, content)
        result = re.sub(r'[\s\t]', '', result)
        self.assertEqual(result, "<span>content</span><div>test</div>")

        body = """
            <body>
                <div>test</div>
            </body>
        """

        result = prepend_html_content(body, content)
        result = re.sub(r'[\s\t]', '', result)
        self.assertEqual(result, "<body><span>content</span><div>test</div></body>")

        body = """
            <html>
                <body>
                    <div>test</div>
                </body>
            </html>
        """

        content = """
            <html>
                <body>
                    <div>test</div>
                </body>
            </html>
        """
        result = prepend_html_content(body, content)
        result = re.sub(r'[\s\t]', '', result)
        self.assertEqual(result, "<html><body><div>test</div><div>test</div></body></html>")


class TestEmailTools(BaseCase):
    """ Test some of our generic utility functions for emails """

    def test_email_split(self):
        cases = [
            ("John <12345@gmail.com>", ['12345@gmail.com']),  # regular form
            ("d@x; 1@2", ['d@x', '1@2']),  # semi-colon + extra space
            ("'(ss)' <123@gmail.com>, 'foo' <foo@bar>", ['123@gmail.com', 'foo@bar']),  # comma + single-quoting
            ('"john@gmail.com"<johnny@gmail.com>', ['johnny@gmail.com']),  # double-quoting
            ('"<jg>" <johnny@gmail.com>', ['johnny@gmail.com']),  # double-quoting with brackets
        ]
        for text, expected in cases:
            self.assertEqual(email_split(text), expected, 'email_split is broken')

    def test_email_formataddr(self):
        email = 'joe@example.com'
        email_idna = 'joe@examplé.com'
        cases = [
            # (name, address),          charsets            expected
            (('', email),               ['ascii', 'utf-8'], 'joe@example.com'),
            (('joe', email),            ['ascii', 'utf-8'], '"joe" <joe@example.com>'),
            (('joe doe', email),        ['ascii', 'utf-8'], '"joe doe" <joe@example.com>'),
            (('joe"doe', email),        ['ascii', 'utf-8'], '"joe\\"doe" <joe@example.com>'),
            (('joé', email),            ['ascii'],          '=?utf-8?b?am/DqQ==?= <joe@example.com>'),
            (('joé', email),            ['utf-8'],          '"joé" <joe@example.com>'),
            (('', email_idna),          ['ascii'],          'joe@xn--exampl-gva.com'),
            (('', email_idna),          ['utf-8'],          'joe@examplé.com'),
            (('joé', email_idna),       ['ascii'],          '=?utf-8?b?am/DqQ==?= <joe@xn--exampl-gva.com>'),
            (('joé', email_idna),       ['utf-8'],          '"joé" <joe@examplé.com>'),
            (('', 'joé@example.com'),   ['ascii', 'utf-8'], 'joé@example.com'),
        ]

        for pair, charsets, expected in cases:
            for charset in charsets:
                with self.subTest(pair=pair, charset=charset):
                    self.assertEqual(formataddr(pair, charset), expected)

    def test_extract_rfc2822_addresses(self):
        tests = [
            ('"Admin" <admin@example.com>', ['admin@example.com']),
            ('"Admin" <admin@example.com>, Demo <demo@test.com>', ['admin@example.com', 'demo@test.com']),
            ('admin@example.com', ['admin@example.com']),
            ('"Admin" <admin@example.com>, Demo <malformed email>', ['admin@example.com']),
            ('admin@éxample.com', ['admin@xn--xample-9ua.com']),
            ('"admin@éxample.com" <admin@éxample.com>', ['admin@xn--xample-9ua.com']),
        ]

        for (rfc2822_email, expected) in tests:
            self.assertEqual(extract_rfc2822_addresses(rfc2822_email), expected)

    def test_email_domain_normalize(self):
        self.assertEqual(email_domain_normalize("Test.Com"), "test.com", "Should have normalized the domain")
        self.assertEqual(email_domain_normalize("email@test.com"), False, "The domain is not valid, should return False")
        self.assertEqual(email_domain_normalize(False), False, "The domain is not valid, should return False")


class EmailConfigCase(TransactionCase):
    @patch.dict("odoo.tools.config.options", {"email_from": "settings@example.com"})
    def test_default_email_from(self, *args):
        """Email from setting is respected."""
        # ICP setting is more important
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("mail.catchall.domain", "example.org")
        ICP.set_param("mail.default.from", "icp")
        message = self.env["ir.mail_server"].build_email(
            False, "recipient@example.com", "Subject",
            "The body of an email",
        )
        self.assertEqual(message["From"], "icp@example.org")
        # Without ICP, the config file/CLI setting is used
        ICP.set_param("mail.default.from", False)
        message = self.env["ir.mail_server"].build_email(
            False, "recipient@example.com", "Subject",
            "The body of an email",
        )
        self.assertEqual(message["From"], "settings@example.com")


class _FakeSMTP:
    """SMTP stub"""
    def __init__(self):
        self.messages = []
        self.from_filter = 'example.com'

    # Python 3 before 3.7.4
    def sendmail(self, smtp_from, smtp_to_list, message_str,
                 mail_options=(), rcpt_options=()):
        self.messages.append(message_str)

    # Python 3.7.4+
    def send_message(self, message, smtp_from, smtp_to_list,
                     mail_options=(), rcpt_options=()):
        self.messages.append(message.as_string())


class TestEmailMessage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._fake_smtp = _FakeSMTP()

    def build_email(self, **kwargs):
        kwargs.setdefault('email_from', 'from@example.com')
        kwargs.setdefault('email_to', 'to@example.com')
        kwargs.setdefault('subject', 'subject')
        return self.env['ir.mail_server'].build_email(**kwargs)

    def send_email(self, msg):
        with patch.object(threading.current_thread(), 'testing', False):
            self.env['ir.mail_server'].send_email(msg, smtp_session=self._fake_smtp)
        return self._fake_smtp.messages.pop()

    def test_bpo_34424_35805(self):
        """Ensure all email sent are bpo-34424 and bpo-35805 free"""
        msg = email.message.EmailMessage(policy=email.policy.SMTP)
        msg['From'] = '"Joé Doe" <joe@example.com>'
        msg['To'] = '"Joé Doe" <joe@example.com>'

        # Message-Id & References fields longer than 77 chars (bpo-35805)
        msg['Message-Id'] = '<929227342217024.1596730490.324691772460938-example-30661-some.reference@test-123.example.com>'
        msg['References'] = '<345227342212345.1596730777.324691772483620-example-30453-other.reference@test-123.example.com>'

        msg_on_the_wire = self.send_email(msg)
        self.assertEqual(msg_on_the_wire,
            'From: =?utf-8?q?Jo=C3=A9?= Doe <joe@example.com>\r\n'
            'To: =?utf-8?q?Jo=C3=A9?= Doe <joe@example.com>\r\n'
            'Message-Id: <929227342217024.1596730490.324691772460938-example-30661-some.reference@test-123.example.com>\r\n'
            'References: <345227342212345.1596730777.324691772483620-example-30453-other.reference@test-123.example.com>\r\n'
            '\r\n'
        )

    def test_alternative_correct_order(self):
        """
        RFC-1521 7.2.3. The Multipart/alternative subtype
        > the alternatives appear in an order of increasing faithfulness
        > to the original content. In general, the best choice is the
        > LAST part of a type supported by the recipient system's local
        > environment.

        Also, the MIME-Version header should be present in BOTH the
        enveloppe AND the parts
        """
        msg = self.build_email(body='<p>Hello world</p>', subtype='html')
        msg_on_the_wire = self.send_email(msg)

        self.assertGreater(msg_on_the_wire.index('text/html'), msg_on_the_wire.index('text/plain'),
            "The html part should be preferred (=appear after) to the text part")
        self.assertEqual(msg_on_the_wire.count('==============='), 2 + 2, # +2 for the header and the footer
            "There should be 2 parts: one text and one html")
        self.assertEqual(msg_on_the_wire.count('MIME-Version: 1.0'), 3,
            "There should be 3 headers MIME-Version: one on the enveloppe, "
            "one on the html part, one on the text part")
