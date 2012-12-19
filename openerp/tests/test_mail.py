#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This test can be run stand-alone with something like:
# > PYTHONPATH=. python2 openerp/tests/test_misc.py
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import unittest2
from openerp.tools import html_sanitize, html_email_clean, append_content_to_html, plaintext2html

HTML_SOURCE = """
<font size="2" style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; ">test1</font>
<div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; font-style: normal; ">
<b>test2</b></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<i>test3</i></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<u>test4</u></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<strike>test5</strike></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; ">
<font size="5">test6</font></div><div><ul><li><font color="#1f1f1f" face="monospace" size="2">test7</font></li><li>
<font color="#1f1f1f" face="monospace" size="2">test8</font></li></ul><div><ol><li><font color="#1f1f1f" face="monospace" size="2">test9</font>
</li><li><font color="#1f1f1f" face="monospace" size="2">test10</font></li></ol></div></div>
<blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;"><div><div><div><font color="#1f1f1f" face="monospace" size="2">
test11</font></div></div></div></blockquote><blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;">
<blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;"><div><font color="#1f1f1f" face="monospace" size="2">
test12</font></div><div><font color="#1f1f1f" face="monospace" size="2"><br></font></div></blockquote></blockquote>
<font color="#1f1f1f" face="monospace" size="2"><a href="http://google.com">google</a></font>
<a href="javascript:alert('malicious code')">test link</a>
"""

TEXT_MAIL1 = """I contact you about our meeting for tomorrow. Here is the schedule I propose:
9 AM: brainstorming about our new amazing business app</span></li>
9.45 AM: summary
10 AM: meeting with Fabien to present our app
Is everything ok for you ?
--
Administrator"""

HTML_MAIL1 = """<div>
<font><span>I contact you about our meeting for tomorrow. Here is the schedule I propose:</span></font>
</div>
<div><ul>
<li><span>9 AM: brainstorming about our new amazing business app</span></li>
<li><span>9.45 AM: summary</span></li>
<li><span>10 AM: meeting with Fabien to present our app</span></li>
</ul></div>
<div><font><span>Is everything ok for you ?</span></font></div>"""

GMAIL_REPLY1_SAN = """Hello,<div><br></div><div>Ok for me. I am replying directly in gmail, without signature.</div><div><br></div><div>Kind regards,</div><div><br></div><div>Demo.<br><br><div>On Thu, Nov 8, 2012 at 5:29 PM,  <span>&lt;<a href="mailto:dummy@example.com">dummy@example.com</a>&gt;</span> wrote:<br><blockquote><div>I contact you about our meeting for tomorrow. Here is the schedule I propose:</div><div><ul><li>9 AM: brainstorming about our new amazing business app&lt;/span&gt;&lt;/li&gt;</li>
<li>9.45 AM: summary</li><li>10 AM: meeting with Fabien to present our app</li></ul></div><div>Is everything ok for you ?</div>
<div><p>--<br>Administrator</p></div>

<div><p>Log in our portal at: <a href="http://localhost:8069#action=login&amp;db=mail_1&amp;login=demo">http://localhost:8069#action=login&amp;db=mail_1&amp;login=demo</a></p></div>
</blockquote></div><br></div>"""

THUNDERBIRD_16_REPLY1_SAN = """    <div>On 11/08/2012 05:29 PM,
      <a href="mailto:dummy@example.com">dummy@example.com</a> wrote:<br></div>
    <blockquote>
      <div>I contact you about our meeting for tomorrow. Here is the
        schedule I propose:</div>
      <div>
        <ul><li>9 AM: brainstorming about our new amazing business
            app&lt;/span&gt;&lt;/li&gt;</li>
          <li>9.45 AM: summary</li>
          <li>10 AM: meeting with Fabien to present our app</li>
        </ul></div>
      <div>Is everything ok for you ?</div>
      <div>
        <p>--<br>
          Administrator</p>
      </div>
      <div>
        <p>Log in our portal at:
<a href="http://localhost:8069#action=login&amp;db=mail_1&amp;token=rHdWcUART5PhEnJRaXjH">http://localhost:8069#action=login&amp;db=mail_1&amp;token=rHdWcUART5PhEnJRaXjH</a></p>
      </div>
    </blockquote>
    Ok for me. I am replying directly below your mail, using
    Thunderbird, with a signature.<br><br>
    Did you receive my email about my new laptop, by the way ?<br><br>
    Raoul.<br><pre>-- 
Raoul Grosbedonn&#233;e
</pre>"""

TEXT_TPL = """Salut Raoul!
Le 28 oct. 2012 à 00:02, Raoul Grosbedon a écrit :

> C'est sûr que je suis intéressé (quote)!

Trouloulou pouet pouet. Je ne vais quand même pas écrire de vrais mails, non mais ho.

> 2012/10/27 Bert Tartopoils :
>> Diantre, me disè-je en envoyant un message similaire à Martine, mais comment vas-tu (quote)?
>> 
>> A la base le contenu était un vrai mail, mais je l'ai quand même réécrit pour ce test, histoire de dire que, quand même, on ne met pas n'importe quoi ici. (quote)
>> 
>> Et sinon bon courage pour trouver tes clefs (quote).
>> 
>> Bert TARTOPOILS
>> bert.tartopoils@miam.miam
>> 
> 
> 
> -- 
> Raoul Grosbedon

Bert TARTOPOILS
bert.tartopoils@miam.miam
"""


class TestSanitizer(unittest2.TestCase):
    """ Test the html sanitizer that filters html to remove unwanted attributes """

    def test_simple(self):
        x = "yop"
        self.assertEqual(x, html_sanitize(x))

    def test_trailing_text(self):
        x = 'lala<p>yop</p>xxx'
        self.assertEqual(x, html_sanitize(x))

    def test_html(self):
        sanitized_html = html_sanitize(HTML_SOURCE)
        for tag in ['<font>', '<div>', '<b>', '<i>', '<u>', '<strike>', '<li>', '<blockquote>', '<a href']:
            self.assertIn(tag, sanitized_html, 'html_sanitize stripped too much of original html')
        for attr in ['style', 'javascript']:
            self.assertNotIn(attr, sanitized_html, 'html_sanitize did not remove enough unwanted attributes')

    def test_unicode(self):
        html_sanitize("Merci à l'intérêt pour notre produit.nous vous contacterons bientôt. Merci")


class TestCleaner(unittest2.TestCase):
    """ Test the email cleaner function that filters the content of incoming emails """

    def test_html_email_clean(self):
        # Test1: reply through gmail: quote in blockquote, signature --\nAdministrator
        new_html = html_email_clean(GMAIL_REPLY1_SAN)
        self.assertNotIn('blockquote', new_html, 'html_email_cleaner did not remove a blockquote')
        self.assertNotIn('I contact you about our meeting', new_html, 'html_email_cleaner wrongly removed the quoted content')
        self.assertNotIn('Administrator', new_html, 'html_email_cleaner did not erase the signature')
        self.assertIn('Ok for me', new_html, 'html_email_cleaner erased too much content')

        # Test2: reply through Tunderbird 16.0.2
        new_html = html_email_clean(THUNDERBIRD_16_REPLY1_SAN)
        self.assertNotIn('blockquote', new_html, 'html_email_cleaner did not remove a blockquote')
        self.assertNotIn('I contact you about our meeting', new_html, 'html_email_cleaner wrongly removed the quoted content')
        self.assertNotIn('Administrator', new_html, 'html_email_cleaner did not erase the signature')
        self.assertNotIn('Grosbedonn', new_html, 'html_email_cleaner did not erase the signature')
        self.assertIn('Ok for me', new_html, 'html_email_cleaner erased too much content')

        # Test3: text email
        new_html = html_email_clean(TEXT_MAIL1)
        self.assertIn('I contact you about our meeting', new_html, 'html_email_cleaner wrongly removed the quoted content')
        self.assertNotIn('Administrator', new_html, 'html_email_cleaner did not erase the signature')

        # Test4: more complex text email
        new_html = html_email_clean(TEXT_TPL)
        self.assertNotIn('quote', new_html, 'html_email_cleaner did not remove correctly plaintext quotes')

        # Test5: False boolean for text must return empty string
        new_html = html_email_clean(False)
        self.assertEqual(new_html, False, 'html_email_cleaner did change a False in an other value.')

        # Test6: Message with xml and doctype tags don't crash
        new_html = html_email_clean(u'<?xml version="1.0" encoding="iso-8859-1"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n <head>\n  <title>404 - Not Found</title>\n </head>\n <body>\n  <h1>404 - Not Found</h1>\n </body>\n</html>\n')
        self.assertNotIn('encoding', new_html, 'html_email_cleaner did not remove correctly encoding attributes')

class TestHtmlTools(unittest2.TestCase):
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


if __name__ == '__main__':
    unittest2.main()
