# Part of Odoo. See LICENSE file for full copyright and licensing details.
# ruff: noqa: W291
# because trailing whitespace are part of the tests
from odoo.tests import TransactionCase
from odoo.tools import html_to_formatted_plaintext


class TestHtmlToPlaintext(TransactionCase):

    def _test_cases(self, cases, options=None):
        options = options or {}
        for case, source, expected in cases:
            with self.subTest(case=case):
                result = html_to_formatted_plaintext(source, **options)
                self.assertEqual(expected.strip(), result)

    def test_html_to_formatted_plaintext(self):
        cases = [
            (
                "Several lines in p",
                "<p>First <br/>Second Paragraph</p><p><hr/></p>",
                "First\nSecond Paragraph\n\n* * *",
            ),
            (
                "Several lines in p (2)",
                "<div><p>First <br/>Second <br/>Third Paragraph</p><p><hr/></p>",
                "First\nSecond\nThird Paragraph\n\n* * *",
            ),
            (
                "Two ps without br",
                "<div><p>First</p><p>Second <br/>Third Paragraph</p><p><hr/></p>",
                "First\n\nSecond\nThird Paragraph\n\n* * *",
            ),
            (
                "Link at the end",
                '<div><p>--<br/>Signature paragraph with a <a href="./link">link</a></p></div>',
                "--\nSignature paragraph with a [link][1]\n\n\n[1]: ./link",
            ),
            (
                "Two peas space",
                "<div><p>One</p><p>Two</p></div>",
                "One\n\nTwo",
            ),
            (
                "Two divs no space",
                "<div>One</div><div>Two</div>",
                "One\nTwo",
            ),
            (
                "Simple link as footnote",
                '<div><p>A <a href="link1">lonely</a> link.</p></div>',
                "A [lonely][1] link.\n\n\n[1]: link1",
            ),
            (
                "Multiple Links at the end",
                '<div><p>A <a href="link1">first</a> link.</p><p>--<br/>Signature paragraph with a <a href="./link">link</a></p></div>',
                "A [first][1] link.\n\n--\nSignature paragraph with a [link][2]"
                "\n\n\n[1]: link1\n[2]: ./link",
            ),
            (
                "Entities and whitespace",
                "<p>Now =&gt; processing&nbsp;entities&#8203;and extra whitespace too.  </p>",
                "Now => processing\u00a0entities\u200band extra whitespace too.",
            ),
            (
                "Unmatched tags",
                "<div>Look what happens with <p>unmatched tags</div>",
                "Look what happens with \nunmatched tags",
            ),
            (
                "Unclosed tags",
                "<div>Look what happens with <p unclosed tags</div> Are we good?",
                "Look what happens with \nAre we good?",
            ),
            (
                "A List",
                "<div>A list of things<ul> <li>One</li><li>Two</li><li> Three</li></ul></div>",
                "A list of things\n* One\n* Two\n* Three\n",
            ),
        ]
        self._test_cases(cases)

    def test_complex_base(self):
        cases = [
            (
                "More peas and beers",
                """<body style="margin: 0; padding: 0; background: #ffffff;-webkit-text-size-adjust: 100%;" data-o-mail-quote-container="1">

  <p>Please call me as soon as possible this afternoon!</p>

  <p data-o-mail-quote="1">--<br data-o-mail-quote="1">
     Sylvie
  </p><p data-o-mail-quote="1">
 </p></body>""",
                "Please call me as soon as possible this afternoon!\n\n--\nSylvie",
            ),
        ]
        self._test_cases(cases)

    def test_complex_html_with_blockquotes(self):
        cases = [
            (
                "MISC_HTML_SOURCE",
                """
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
test12<br>blabla</font></div><div><font color="#1f1f1f" face="monospace" size="2"><br></font></div></blockquote></blockquote>
<font color="#1f1f1f" face="monospace" size="2"><a href="https://google.com">google</a></font>
<a href="javascript:alert('malicious code')">test link</a>
""",
                """test1
**test2**
*test3*
*test4*
~~test5~~
test6
* test7
* test8

1. test9
2. test10

> test11

> > test12
> > blabla


[google][1] test link


[1]: https://google.com
""",
            ),
        ]
        self._test_cases(cases)

    def test_html_to_formatted_plaintext_link_inline(self):
        cases = [
            (
                "Inline links",
                '<div><p>Paragraph with a <a href="./link">link</a></p></div>',
                "Paragraph with a [link](./link)",
            ),
            (
                "Multiple Inline links",
                "<div>"
                '<p>Paragraph with a <a href="./link">link</a></p>'
                '<p>And another <a href="./link_here">Here</a></p>'
                "</div>",
                "Paragraph with a [link](./link)\n\nAnd another [Here](./link_here)",
            ),
            (
                "Link with nested label",
                '<p>Paragraph with a link in a <a href="./link">Button</a></p>',
                "Paragraph with a link in a [Button](./link)",
            ),
        ]
        self._test_cases(cases, options={"inline_links": True})

    def test_html_to_formatted_plaintext_default_keeps_images(self):
        cases = [
            (
                "Inline image",
                '<div><p>Hello <img src="./src"/></p></div>',
                "Hello ![Image][1]\n\n\n[1]: ./src",
            ),
        ]
        self._test_cases(cases)

    def test_html_to_formatted_plaintext_handling_inline_images(self):
        cases = [
            (
                "Inline image",
                '<div><p>Paragraph with an <img src="./src.png"/></p></div>',
                "Paragraph with an ![src](./src.png)",
            ),
        ]
        self._test_cases(cases, options={"inline_images": True})

    def test_html_to_formatted_plaintext_handling_footnotes_link_and_images(self):
        cases = [
            (
                "Link and image at the end",
                '<div><p>--<br/>Signature paragraph with a <a href="./link">link</a>'
                '<img src="a_dog.png"/></p></div>',
                "--\nSignature paragraph with a [link][1]![a_dog][2]\n\n\n[1]: ./link\n[2]: a_dog.png",
            ),
        ]
        self._test_cases(cases)

    def test_html_to_formatted_plaintext_handling_inline_link_and_images(self):
        cases = [
            (
                "Link and image at the end",
                '<div><p>--<br/>Signature paragraph with a <a href="./link">link</a>'
                '<img src="a_dog.png"/></p></div>',
                "--\nSignature paragraph with a [link](./link)![a_dog](a_dog.png)",
            ),
        ]
        self._test_cases(cases, options={"inline_links": True, "inline_images": True})

    def test_html_to_formatted_plaintext_handling_inline_link_and_footnote_images(self):
        cases = [
            (
                "Link and image at the end",
                '<div><p>--<br/>Signature paragraph with a <a href="./link">link</a>'
                '<img src="a_dog.png"/></p></div>',
                "--\nSignature paragraph with a [link](./link)![a_dog][1]\n\n\n[1]: a_dog.png",
            ),
        ]
        self._test_cases(cases, options={"inline_links": True})

    def test_html_to_formatted_plaintext_handling_footnote_link_and_inline_image(self):
        cases = [
            (
                "Link and image at the end",
                '<div><p>--<br/>Signature paragraph with a <a href="./link">link</a>'
                '<img src="a_dog.png"/></p></div>',
                "--\nSignature paragraph with a [link][1]![a_dog](a_dog.png)\n\n\n[1]: ./link",
            ),
        ]
        self._test_cases(cases, options={"inline_images": True})

    def test_titles(self):
        cases = [
            (
                "Titles and some content",
                """<h1>Title</h1>
<h2>Sub title</h2>
<br/>
<h3>Sub sub title</h3>
<h4>Sub sub sub title</h4>
<p>Paragraph <em>with</em> <b>bold</b></p>
""",
                """# Title

## Sub title

### Sub sub title

#### Sub sub sub title

Paragraph *with* **bold**
             """,
            )
        ]
        self._test_cases(cases)

    def test_tables(self):
        cases = [
            (
                "2x1",
                "<table><tr><td>table element 1</td></tr><tr><td>table element 2</td></tr></table>",
                """table element 1\ntable element 2""",
            ),
            (
                "2x2",
                """<table><tr><td>table element 1</td><td>table element 2</td></tr>
                <tr><td>table element 3</td><td>table element 4</td></tr></table>""",
                "table element 1 table element 2\ntable element 3 table element 4",
            ),
        ]
        self._test_cases(cases)

    def test_varia(self):
        cases = [
            (
                "QUOTE_THUNDERBIRD_HTML",
                """<html>
  <head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
  </head>
  <body text="#000000" bgcolor="#FFFFFF">
    <div class="moz-cite-prefix">On 01/05/2016 10:24 AM, Raoul
      Poilvache wrote:<br>
    </div>
    <blockquote
cite="mid:CAP76m_WWFH2KVrbjOxbaozvkmbzZYLWJnQ0n0sy9XpGaCWRf1g@mail.gmail.com"
      type="cite">
      <div dir="ltr"><b><i>Test reply. The suite.</i></b><br clear="all">
        <div><br>
        </div>
        -- <br>
        <div class="gmail_signature">Raoul Poilvache</div>
      </div>
    </blockquote>
    Top cool !!!<br>
    <br>
    <pre class="moz-signature" cols="72">-- 
Raoul Poilvache
</pre>
  </body>
</html>""",
                """On 01/05/2016 10:24 AM, Raoul Poilvache wrote:
> ***Test reply. The suite.***
> 
> --
> Raoul Poilvache

Top cool !!!

-- 
Raoul Poilvache""",
            ),
        ]
        self._test_cases(cases)

    def test_strip_links(self):
        cases = [
            (
                "strip all links",
                """<p>This is a <a href="blabla">link</a> and this is an image: <img src="blabla"/></p>""",
                "This is a link and this is an image:"
            ),
        ]
        self._test_cases(cases, options={"strip_links": True})

        cases = [
            (
                "strip images",
                """<p>This is a <a href="blabla">link</a> and this is an image: <img src="blabla"/></p>""",
                "This is a [link][1] and this is an image:\n\n\n[1]: blabla"
            ),
        ]
        self._test_cases(cases, options={"strip_images": True})
