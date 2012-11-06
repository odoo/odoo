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
from openerp.tools.mail import html_sanitize, html_email_clean, append_content_to_html

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

GMAIL_REPLY = """<html>
  <head>
    <meta content="text/html; charset=ISO-8859-1"
      http-equiv="Content-Type">
  </head>
  <body text="#000000" bgcolor="#FFFFFF">
    <div class="moz-cite-prefix">R&eacute;ponse via thunderbird, classique.<br>
      <br>
      On 11/05/2012 10:51 AM, Thibault Delavall&eacute;e wrote:<br>
    </div>
    <blockquote
cite="mid:CAP76m_WwG6=dY1aYYBJpJHvFtFk31YYjMoHoZaDRpPmacn+Ohw@mail.gmail.com"
      type="cite">
      <div>Plop !</div>
      <ul>
        <li>Vive les lapins rapides !<br>
        </li>
        <li>Nouille</li>
        <li>Frites</li>
      </ul>
      <div><br>
      </div>
      <div>Clairement, hein ?</div>
      -- <br>
      Thibault Delavall&eacute;e<br>
    </blockquote>
    <br>
    <br>
    <pre class="moz-signature" cols="72">-- 
Thibault Delavall&eacute;e
</pre>
  </body>
</html>"""

GAMIL_REPLY_SAN = """<div>R&#233;ponse via thunderbird, classique.<br><br>
      On 11/05/2012 10:51 AM, Thibault Delavall&#233;e wrote:<br></div>
    <blockquote>
      <div>Plop !</div>
      <ul><li>Vive les lapins rapides !<br></li>
        <li>Nouille</li>
        <li>Frites</li>
      </ul><div><br></div>
      <div>Clairement, hein ?</div>
      -- <br>
      Thibault Delavall&#233;e<br></blockquote>
    <br><br><pre>-- 
Thibault Delavall&#233;e
</pre>"""




GMAIL_REPLY2_SAN = """<div>Je r&#233;ponds, hop, via thunderbird. Mais
      je vais r&#233;podnre aussi au milieu du thread.<br><br>
      On 11/05/2012 10:53 AM, Thibault Delavall&#233;e wrote:<br></div>
    <blockquote>Reply rapide de gmail.</blockquote>
    <br>
    Jamais.<br><br><blockquote>
      <div><br><br><div>2012/11/5 Thibault Delavall&#233;e <span>&lt;<a href="mailto:tde@openerp.com">tde@openerp.com</a>&gt;</span><br><blockquote>
            <div>
              <div>R&#233;ponse via thunderbird, classique.
                <div>
                  <div><br><br>
                    On 11/05/2012 10:51 AM, Thibault Delavall&#233;e wrote:<br></div>
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
                    Thibault Delavall&#233;e<br></blockquote>
                  <br><br></div>
              </div>
              <span><font>
                  <pre>-- 
Thibault Delavall&#233;e
</pre>
                </font></span></div>
          </blockquote>
        </div>
        <br><br><div><br></div>
        -- <br>
        Thibault Delavall&#233;e<br></div>
    </blockquote>
    <br><br><pre>-- 
Thibault Delavall&#233;e
</pre>"""



MAIL_TEMPLATE = """Hey XYZ,

I've fixed that error and tested it a couple of times, it seems to be working
fine now.

On Fri, Feb 18, 2011 at 7:44 AM, Joe David <joe@david.com> wrote:
Initial thread starts here...

--
Thanks
joe@david.com
"""

GMAIL_TPL = """Salut Bob!
Le 28 oct. 2012 à 00:02, Thibault Delavallée a écrit :

> MatrixPlus le 22/02 ? Si c'est ce que tu dis, je suis intéressé, oui !

Non, pas MatrixPlus, juste Matrix.

Et oui, le 22/02 est la date qui doit vous convenir le deux.

Bon, on tente de s’organiser un truc se samedi-là et je réserve des places.

En passant, t’as contacté les gens du KdM pour le truc pour Bénisexe ?

> 2012/10/27 Édouard Gilbert :
>> Diantre, me disè-je en envoyant un message similaire à Koukouiles, que ne voilà un concert qui pourrait intéresser Thibault ?
>> 
>> L’ONL donne, en février et à Lille, Matrix en ciné-concert. Il passe le film sans musique mais c’est pas grave parce qu’il y a un orchestre qui la joue en même temps. Intéressé ?
>> 
>> On peut trouver plus d’info sur le site de l’ONL, onlille.com , mais il est tellement mal foutu que je ne trouve pas de lien direct. Je te laisse chercher.
>> 
>> Édouard GILBERT
>> edouard.gilbert@gmail.com
>> 
> 
> 
> 
> -- 
> Thibault Delavallée

Édouard GILBERT
edouard.gilbert@gmail.com
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
        test_case = """youplaboum"""
        html_email_clean(test_case)


if __name__ == '__main__':
    unittest2.main()
