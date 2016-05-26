#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This test can be run stand-alone with something like:
# > PYTHONPATH=. python2 openerp/tests/test_misc.py
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import cgi
import lxml
import unittest

from openerp.tools import html_sanitize, html_email_clean, append_content_to_html, plaintext2html, email_split
import test_mail_examples


class TestSanitizer(unittest.TestCase):
    """ Test the html sanitizer that filters html to remove unwanted attributes """

    def test_basic_sanitizer(self):
        cases = [
            ("yop", "<p>yop</p>"),  # simple
            ("lala<p>yop</p>xxx", "<p>lala</p><p>yop</p>xxx"),  # trailing text
            ("Merci à l'intérêt pour notre produit.nous vous contacterons bientôt. Merci",
                u"<p>Merci à l'intérêt pour notre produit.nous vous contacterons bientôt. Merci</p>"),  # unicode
        ]
        for content, expected in cases:
            html = html_sanitize(content)
            self.assertEqual(html, expected, 'html_sanitize is broken')

    def test_mako(self):
        cases = [
            ('''<p>Some text</p>
<% set signup_url = object.get_signup_url() %>
% if signup_url:
<p>
    You can access this document and pay online via our Customer Portal:
</p>''', '''<p>Some text</p>
<% set signup_url = object.get_signup_url() %>
% if signup_url:
<p>
    You can access this document and pay online via our Customer Portal:
</p>''')
        ]
        for content, expected in cases:
            html = html_sanitize(content, silent=False)
            self.assertEqual(html, expected, 'html_sanitize: broken mako management')

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
            ("<BODY BACKGROUND=\"javascript:alert('XSS')\">"),  # body image
            ("<IMG DYNSRC=\"javascript:alert('XSS')\">"),  # img dynsrc
            ("<IMG LOWSRC=\"javascript:alert('XSS')\">"),  # img lowsrc
            ("<TABLE BACKGROUND=\"javascript:alert('XSS')\">"),  # table
            ("<TABLE><TD BACKGROUND=\"javascript:alert('XSS')\">"),  # td
            ("<DIV STYLE=\"background-image: url(javascript:alert('XSS'))\">"),  # div background
            ("<DIV STYLE=\"background-image:\0075\0072\006C\0028'\006a\0061\0076\0061\0073\0063\0072\0069\0070\0074\003a\0061\006c\0065\0072\0074\0028.1027\0058.1053\0053\0027\0029'\0029\">"),  # div background with unicoded exploit
            ("<DIV STYLE=\"background-image: url(&#1;javascript:alert('XSS'))\">"),  # div background + extra characters
            ("<IMG SRC='vbscript:msgbox(\"XSS\")'>"),  # VBscrip in an image
            ("<BODY ONLOAD=alert('XSS')>"),  # event handler
            ("<BR SIZE=\"&{alert('XSS')}\>"),  # & javascript includes
            ("<LINK REL=\"stylesheet\" HREF=\"javascript:alert('XSS');\">"),  # style sheet
            ("<LINK REL=\"stylesheet\" HREF=\"http://ha.ckers.org/xss.css\">"),  # remote style sheet
            ("<STYLE>@import'http://ha.ckers.org/xss.css';</STYLE>"),  # remote style sheet 2
            ("<META HTTP-EQUIV=\"Link\" Content=\"<http://ha.ckers.org/xss.css>; REL=stylesheet\">"),  # remote style sheet 3
            ("<STYLE>BODY{-moz-binding:url(\"http://ha.ckers.org/xssmoz.xml#xss\")}</STYLE>"),  # remote style sheet 4
            ("<IMG STYLE=\"xss:expr/*XSS*/ession(alert('XSS'))\">"),  # style attribute using a comment to break up expression
        ]
        for content in cases:
            html = html_sanitize(content)
            self.assertNotIn('javascript', html, 'html_sanitize did not remove a malicious javascript')
            self.assertTrue('ha.ckers.org' not in html or 'http://ha.ckers.org/xss.css' in html, 'html_sanitize did not remove a malicious code in %s (%s)' % (content, html))

        content = "<!--[if gte IE 4]><SCRIPT>alert('XSS');</SCRIPT><![endif]-->"  # down-level hidden block
        self.assertEquals(html_sanitize(content, silent=False), '')

    def test_html(self):
        sanitized_html = html_sanitize(test_mail_examples.MISC_HTML_SOURCE)
        for tag in ['<div', '<b', '<i', '<u', '<strike', '<li', '<blockquote', '<a href']:
            self.assertIn(tag, sanitized_html, 'html_sanitize stripped too much of original html')
        for attr in ['javascript']:
            self.assertNotIn(attr, sanitized_html, 'html_sanitize did not remove enough unwanted attributes')

    def test_sanitize_escape_emails(self):
        emails = [
            "Charles <charles.bidule@truc.fr>",
            "Dupuis <'tr/-: ${dupuis#$'@truc.baz.fr>",
            "Technical <service/technical+2@open.com>",
            "Div nico <div-nico@open.com>"
        ]
        for email in emails:
            self.assertIn(cgi.escape(email), html_sanitize(email), 'html_sanitize stripped emails of original html')

    def test_sanitize_escape_emails_cite(self):
        not_emails = [
            '<blockquote cite="mid:CAEJSRZvWvud8c6Qp=wfNG6O1+wK3i_jb33qVrF7XyrgPNjnyUA@mail.gmail.com" type="cite">cat</blockquote>']
        for email in not_emails:
            sanitized = html_sanitize(email)
            self.assertNotIn(cgi.escape(email), sanitized, 'html_sanitize stripped emails of original html')
            self.assertIn(
                '<blockquote cite="mid:CAEJSRZvWvud8c6Qp=wfNG6O1+wK3i_jb33qVrF7XyrgPNjnyUA@mail.gmail.com"',
                sanitized,
                'html_sanitize escaped valid address-like')

    def test_edi_source(self):
        html = html_sanitize(test_mail_examples.EDI_LIKE_HTML_SOURCE)
        self.assertIn('div style="font-family: \'Lucida Grande\', Ubuntu, Arial, Verdana, sans-serif; font-size: 12px; color: rgb(34, 34, 34); background-color: #FFF;', html,
            'html_sanitize removed valid style attribute')
        self.assertIn('<span style="color: #222; margin-bottom: 5px; display: block; ">', html,
            'html_sanitize removed valid style attribute')
        self.assertIn('img class="oe_edi_paypal_button" src="https://www.paypal.com/en_US/i/btn/btn_paynowCC_LG.gif"', html,
            'html_sanitize removed valid img')
        self.assertNotIn('</body></html>', html, 'html_sanitize did not remove extra closing tags')


class TestCleaner(unittest.TestCase):
    """ Test the email cleaner function that filters the content of incoming emails """

    def test_00_basic_text(self):
        """ html_email_clean test for signatures """
        test_data = [
            (
                """This is Sparta!\n--\nAdministrator\n+9988776655""",
                ['This is Sparta!'],
                ['Administrator', '9988776655']
            ), (
                """<p>--\nAdministrator</p>""",
                [],
                ['--', 'Administrator']
            ), (
                """<p>This is Sparta!\n---\nAdministrator</p>""",
                ['This is Sparta!'],
                ['---', 'Administrator']
            ), (
                """<p>--<br>Administrator</p>""",
                [],
                []
            ), (
                """<p>This is Sparta!<br/>--<br>Administrator</p>""",
                ['This is Sparta!'],
                []
            ), (
                """This is Sparta!\n>Ah bon ?\nCertes\n> Chouette !\nClair""",
                ['This is Sparta!', 'Certes', 'Clair'],
                ['Ah bon', 'Chouette']
            )
        ]
        for test, in_lst, out_lst in test_data:
            new_html = html_email_clean(test, remove=True)
            for text in in_lst:
                self.assertIn(text, new_html, 'html_email_cleaner wrongly removed content')
            for text in out_lst:
                self.assertNotIn(text, new_html, 'html_email_cleaner did not remove unwanted content')

    def test_05_shorten(self):
        # TEST: shorten length
        test_str = '''<div>
        <span>
        </span>
        <p>Hello, <span>Raoul</span> 
    <bold>You</bold> are 
    pretty</p>
<span>Really</span>
</div>
'''
        # shorten at 'H' of Hello -> should shorten after Hello,
        html = html_email_clean(test_str, shorten=True, max_length=1, remove=True)
        self.assertIn('Hello,', html, 'html_email_cleaner: shorten error or too short')
        self.assertNotIn('Raoul', html, 'html_email_cleaner: shorten error or too long')
        self.assertIn('read more', html, 'html_email_cleaner: shorten error about read more inclusion')
        # shorten at 'are' -> should shorten after are
        html = html_email_clean(test_str, shorten=True, max_length=17, remove=True)
        self.assertIn('Hello,', html, 'html_email_cleaner: shorten error or too short')
        self.assertIn('Raoul', html, 'html_email_cleaner: shorten error or too short')
        self.assertIn('are', html, 'html_email_cleaner: shorten error or too short')
        self.assertNotIn('pretty', html, 'html_email_cleaner: shorten error or too long')
        self.assertNotIn('Really', html, 'html_email_cleaner: shorten error or too long')
        self.assertIn('read more', html, 'html_email_cleaner: shorten error about read more inclusion')

        # TEST: shorten in quote
        test_str = '''<div> Blahble         
            bluih      blouh   
        <blockquote>This is a quote
        <span>And this is quite a long quote, after all.</span>
        </blockquote>
</div>'''
        # shorten in the quote
        html = html_email_clean(test_str, shorten=True, max_length=25, remove=True)
        self.assertIn('Blahble', html, 'html_email_cleaner: shorten error or too short')
        self.assertIn('bluih', html, 'html_email_cleaner: shorten error or too short')
        self.assertIn('blouh', html, 'html_email_cleaner: shorten error or too short')
        self.assertNotIn('quote', html, 'html_email_cleaner: shorten error or too long')
        self.assertIn('read more', html, 'html_email_cleaner: shorten error about read more inclusion')
        # shorten in second word
        html = html_email_clean(test_str, shorten=True, max_length=9, remove=True)
        self.assertIn('Blahble', html, 'html_email_cleaner: shorten error or too short')
        self.assertIn('bluih', html, 'html_email_cleaner: shorten error or too short')
        self.assertNotIn('blouh', html, 'html_email_cleaner: shorten error or too short')
        self.assertNotIn('quote', html, 'html_email_cleaner: shorten error or too long')
        self.assertIn('read more', html, 'html_email_cleaner: shorten error about read more inclusion')
        # shorten waaay too large
        html = html_email_clean(test_str, shorten=True, max_length=900, remove=True)
        self.assertIn('Blahble', html, 'html_email_cleaner: shorten error or too short')
        self.assertIn('bluih', html, 'html_email_cleaner: shorten error or too short')
        self.assertIn('blouh', html, 'html_email_cleaner: shorten error or too short')
        self.assertNotIn('quote', html, 'html_email_cleaner: shorten error or too long')

    def test_10_email_text(self):
        """ html_email_clean test for text-based emails """
        new_html = html_email_clean(test_mail_examples.TEXT_1, remove=True)
        for ext in test_mail_examples.TEXT_1_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.TEXT_1_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

        new_html = html_email_clean(test_mail_examples.TEXT_2, remove=True)
        for ext in test_mail_examples.TEXT_2_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.TEXT_2_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

    def test_20_email_html(self):
        new_html = html_email_clean(test_mail_examples.HTML_1, remove=True)
        for ext in test_mail_examples.HTML_1_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.HTML_1_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

        new_html = html_email_clean(test_mail_examples.HTML_2, remove=True)
        for ext in test_mail_examples.HTML_2_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.HTML_2_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

        # --- MAIL ORIGINAL --- -> can't parse this one currently, too much language-dependent
        # new_html = html_email_clean(test_mail_examples.HTML_3, remove=False)
        # for ext in test_mail_examples.HTML_3_IN:
        #     self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        # for ext in test_mail_examples.HTML_3_OUT:
        #     self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

    def test_30_email_msoffice(self):
        new_html = html_email_clean(test_mail_examples.MSOFFICE_1, remove=True)
        for ext in test_mail_examples.MSOFFICE_1_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.MSOFFICE_1_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

        new_html = html_email_clean(test_mail_examples.MSOFFICE_2, remove=True)
        for ext in test_mail_examples.MSOFFICE_2_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.MSOFFICE_2_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

        new_html = html_email_clean(test_mail_examples.MSOFFICE_3, remove=True)
        for ext in test_mail_examples.MSOFFICE_3_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.MSOFFICE_3_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

    def test_40_email_hotmail(self):
        new_html = html_email_clean(test_mail_examples.HOTMAIL_1, remove=True)
        for ext in test_mail_examples.HOTMAIL_1_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.HOTMAIL_1_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

    def test_50_email_gmail(self):
        new_html = html_email_clean(test_mail_examples.GMAIL_1, remove=True)
        for ext in test_mail_examples.GMAIL_1_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.GMAIL_1_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

    def test_60_email_thunderbird(self):
        new_html = html_email_clean(test_mail_examples.THUNDERBIRD_1, remove=True)
        for ext in test_mail_examples.THUNDERBIRD_1_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.THUNDERBIRD_1_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase signature / quoted content')

    def test_70_read_more_and_shorten(self):
        expand_options = {
            'oe_expand_container_class': 'span_class',
            'oe_expand_container_content': 'Herbert Einstein',
            'oe_expand_separator_node': 'br_lapin',
            'oe_expand_a_class': 'a_class',
            'oe_expand_a_content': 'read mee',
        }
        new_html = html_email_clean(test_mail_examples.OERP_WEBSITE_HTML_1, remove=True, shorten=True, max_length=100, expand_options=expand_options)
        for ext in test_mail_examples.OERP_WEBSITE_HTML_1_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.OERP_WEBSITE_HTML_1_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase overlimit content')
        for ext in ['<span class="span_class">Herbert Einstein<br_lapin></br_lapin><a href="#" class="a_class">read mee</a></span>']:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly take into account specific expand options')

        new_html = html_email_clean(test_mail_examples.OERP_WEBSITE_HTML_2, remove=True, shorten=True, max_length=200, expand_options=expand_options, protect_sections=False)
        for ext in test_mail_examples.OERP_WEBSITE_HTML_2_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.OERP_WEBSITE_HTML_2_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase overlimit content')
        for ext in ['<span class="span_class">Herbert Einstein<br_lapin></br_lapin><a href="#" class="a_class">read mee</a></span>']:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly take into account specific expand options')

        new_html = html_email_clean(test_mail_examples.OERP_WEBSITE_HTML_2, remove=True, shorten=True, max_length=200, expand_options=expand_options, protect_sections=True)
        for ext in test_mail_examples.OERP_WEBSITE_HTML_2_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed not quoted content')
        for ext in test_mail_examples.OERP_WEBSITE_HTML_2_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not erase overlimit content')
        for ext in [
                '<span class="span_class">Herbert Einstein<br_lapin></br_lapin><a href="#" class="a_class">read mee</a></span>',
                'tasks using the gantt chart and control deadlines']:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly take into account specific expand options')

    def test_70_read_more(self):
        new_html = html_email_clean(test_mail_examples.BUG1, remove=True, shorten=True, max_length=100)
        for ext in test_mail_examples.BUG_1_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed valid content')
        for ext in test_mail_examples.BUG_1_OUT:
            self.assertNotIn(ext.decode('utf-8'), new_html, 'html_email_cleaner did not removed invalid content')

        new_html = html_email_clean(test_mail_examples.BUG2, remove=True, shorten=True, max_length=250)
        for ext in test_mail_examples.BUG_2_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed valid content')
        for ext in test_mail_examples.BUG_2_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not removed invalid content')

        new_html = html_email_clean(test_mail_examples.BUG3, remove=True, shorten=True, max_length=250)
        for ext in test_mail_examples.BUG_3_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed valid content')
        for ext in test_mail_examples.BUG_3_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not removed invalid content')

    def test_80_remove_classes(self):
        new_html = html_email_clean(test_mail_examples.REMOVE_CLASS, remove=True)
        for ext in test_mail_examples.REMOVE_CLASS_IN:
            self.assertIn(ext, new_html, 'html_email_cleaner wrongly removed classes')
        for ext in test_mail_examples.REMOVE_CLASS_OUT:
            self.assertNotIn(ext, new_html, 'html_email_cleaner did not removed correctly unwanted classes')

    def test_90_misc(self):
        # False boolean for text must return empty string
        new_html = html_email_clean(False)
        self.assertEqual(new_html, False, 'html_email_cleaner did change a False in an other value.')

        # Message with xml and doctype tags don't crash
        new_html = html_email_clean(u'<?xml version="1.0" encoding="iso-8859-1"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n <head>\n  <title>404 - Not Found</title>\n </head>\n <body>\n  <h1>404 - Not Found</h1>\n </body>\n</html>\n')
        self.assertNotIn('encoding', new_html, 'html_email_cleaner did not remove correctly encoding attributes')


class TestHtmlTools(unittest.TestCase):
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

    def test_append_to_html(self):
        test_samples = [
            ('<!DOCTYPE...><HTML encoding="blah">some <b>content</b></HtMl>', '--\nYours truly', True, True, False,
             '<!DOCTYPE...><html encoding="blah">some <b>content</b>\n<pre>--\nYours truly</pre>\n</html>'),
            ('<!DOCTYPE...><HTML encoding="blah">some <b>content</b></HtMl>', '--\nYours truly', True, False, False,
             '<!DOCTYPE...><html encoding="blah">some <b>content</b>\n<p>--<br/>Yours truly</p>\n</html>'),
            ('<html><body>some <b>content</b></body></html>', '<!DOCTYPE...>\n<html><body>\n<p>--</p>\n<p>Yours truly</p>\n</body>\n</html>', False, False, False,
             '<html><body>some <b>content</b>\n\n\n<p>--</p>\n<p>Yours truly</p>\n\n\n</body></html>'),
        ]
        for html, content, plaintext_flag, preserve_flag, container_tag, expected in test_samples:
            self.assertEqual(append_content_to_html(html, content, plaintext_flag, preserve_flag, container_tag), expected, 'append_content_to_html is broken')


class TestEmailTools(unittest.TestCase):
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

if __name__ == '__main__':
    unittest.main()
