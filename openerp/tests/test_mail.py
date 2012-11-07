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
from openerp.tools.mail import html_sanitize, html_email_clean, append_content_to_html, text2html

test_case = """
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

GMAIL_REPLY_SAN = """<div>R&#233;ponse via thunderbird, classique.<br><br>
      On 11/05/2012 10:51 AM, Raoul Tartopoils wrote:<br></div>
    <blockquote>
      <div>Plop !</div>
      <ul><li>Vive les lapins rapides !<br></li>
        <li>Nouille</li>
        <li>Frites</li>
      </ul><div><br></div>
      <div>Clairement, hein ?</div>
      -- <br>
      Raoul Tartopoils<br></blockquote>
    <br><br><pre>-- 
Raoul Tartopoils
</pre>"""

GMAIL_REPLY2_SAN = """<div>Je r&#233;ponds, hop, via thunderbird. Mais
      je vais r&#233;podnre aussi au milieu du thread.<br><br>
      On 11/05/2012 10:53 AM, Raoul Tartopoils wrote:<br></div>
    <blockquote>Reply rapide de gmail.</blockquote>
    <br>
    Jamais.<br><br><blockquote>
      <div><br><br><div>2012/11/5 Thibault Delavall&#233;e <span>&lt;<a href="mailto:tde@openerp.com">tde@openerp.com</a>&gt;</span><br><blockquote>
            <div>
              <div>R&#233;ponse via thunderbird, classique.
                <div>
                  <div><br><br>
                    On 11/05/2012 10:51 AM, Raoul Tartopoils wrote:<br></div>
                </div>
              </div>
              <div>
                <div>
                  <blockquote>
                    <div>Plop !</div>
                    <ul><li>Vive les lapins rapides !<br></li>
                      <li>Nouille</li>
                    </ul></blockquote>
                </div>
              </div>
            </div>
          </blockquote>
        </div>
      </div>
    </blockquote>
    je rajotuerais bien pommes de terre dans la liste.<br><blockquote>
      <div>
        <div>
          <blockquote>
            <div>
              <div>
                <div>
                  <blockquote>
                    <ul><li>Frites</li>
                    </ul><div><br></div>
                    <div>Clairement, hein ?</div>
                    -- <br>
                    Raoul Tartopoils<br></blockquote>
                  <br><br></div>
              </div>
              <span><font>
                  <pre>-- 
Raoul Tartopoils
</pre>
                </font></span></div>
          </blockquote>
        </div>
        <br><br><div><br></div>
        -- <br>
        Raoul Tartopoils<br></div>
    </blockquote>
    <br><br><pre>-- 
Raoul Tartopoils
</pre>"""


TEXT_TPL = """Salut Raoul!
Le 28 oct. 2012 à 00:02, Raoul Grosbedon a écrit :

> C'est sûr que je suis intéressé (quote)!

Trouloulou pouet pouet.

Je ne vais quand même pas écrire de vrais mails, non mais ho.

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
> 
> -- 
> Raoul Grosbedon

Bert TARTOPOILS
bert.tartopoils@miam.miam
"""


class TestAppendContentToHtml(unittest2.TestCase):
    """ Test some of our generic utility functions """

    def test_append_to_html(self):
        test_samples = [
            ('<!DOCTYPE...><HTML encoding="blah">some <b>content</b></HtMl>', '--\nYours truly', True,
             '<!DOCTYPE...><html encoding="blah">some <b>content</b>\n<pre>--\nYours truly</pre>\n</html>'),
            ('<html><body>some <b>content</b></body></html>', '<!DOCTYPE...>\n<html><body>\n<p>--</p>\n<p>Yours truly</p>\n</body>\n</html>', False,
             '<html><body>some <b>content</b>\n\n\n<p>--</p>\n<p>Yours truly</p>\n\n\n</body></html>'),
        ]
        for html, content, flag, expected in test_samples:
            self.assertEqual(append_content_to_html(html, content, flag), expected, 'append_content_to_html is broken')


class TestSanitizer(unittest2.TestCase):
    # TDE note: could be improved by actually checking the output

    def test_simple(self):
        x = "yop"
        self.assertEqual(x, html_sanitize(x))

    def test_trailing_text(self):
        x = 'lala<p>yop</p>xxx'
        self.assertEqual(x, html_sanitize(x))

    def test_no_exception(self):
        html_sanitize(test_case)

    def test_unicode(self):
        html_sanitize("Merci à l'intérêt pour notre produit.nous vous contacterons bientôt. Merci")


class TestCleaner(unittest2.TestCase):

    def test_gmail(self):
        # Test1: blahblah
        new_html = html_email_clean(GMAIL_REPLY_SAN)
        self.assertNotIn(new_html, 'blockquote')
        self.assertNotIn(new_html, 'Vive les lapins rapides !')
        self.assertNotIn(new_html, 'Bert Tartopoils')


class TestText2Html(unittest2.TestCase):

    def test_text2html(self):
        cases = [
            ("First \nSecond \nThird\n \nParagraph\n\r--\nSignature paragraph", 'div',
             "<div><p>First <br/>Second <br/>Third</p><p>Paragraph</p><p>--<br/>Signature paragraph</p></div>"),
        ]
        for content, container_tag, expected in cases:
            html = text2html(content, container_tag)
            self.assertEqual(html, expected, 'text2html is broken')


if __name__ == '__main__':
    unittest2.main()
