# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from markupsafe import Markup

from odoo.tests import common, tagged
from odoo.tools import mute_logger
from odoo.tools.mail import TEXT_URL_REGEX


@tagged('-at_install', 'post_install')
class TestMailRenderMixin(common.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_url = cls.env["mail.render.mixin"].get_base_url()

    @mute_logger("odoo.tests.common.requests")
    def test_shorten_links(self):
        test_links = [
            '<a href="https://gitlab.com" title="title" fake="fake">test_label</a>',
            '<a href="https://test_542152qsdqsd.com"/>',
            """<a href="https://third_test_54212.com">
                    <img src="imagesrc"/>
                </a>
            """,
            """<a href="https://fourthtesthasnolabel.com">
                    <img/><!-- Really what is this -->
                </a>
            """,
            """<a
                    href="https://test_strange_html.com"       title="title"
                fake='fake'
                > test_strange_html_label
                </a>
            """,
            '<a href="https://test_escaped.com" title="title" fake="fake"> test_escaped &lt; &gt; </a>',
            '<a href="https://url_with_params.com?a=b&c=d">label</a>',
            '<a href="#"></a>',
            '<a href="mailto:afunemail@somewhere.com">email label</a>',
            '<a href="https://www.odoo.com?test=%20+3&amp;this=that">THERE > there</a>',
            '<a >Without href</a>'
        ]

        self.env["mail.render.mixin"]._shorten_links("".join(test_links), {})

        trackers_to_find = [
            [("url", "=", "https://gitlab.com"), ("label", "=", "test_label")],
            [("url", "=", "https://test_542152qsdqsd.com")],
            [("url", "=", "https://third_test_54212.com"), ("label", "=", "[media] imagesrc")],
            [("url", "=", "https://fourthtesthasnolabel.com"), ("label", "=", False)],
            [
                ("url", "=", "https://test_strange_html.com"),
                ("label", "=", "test_strange_html_label"),
            ],
            [
                ("url", "=", "https://test_escaped.com"),
                ("label", "=", "test_escaped < >"),
            ],
            [
                ("url", "=", "https://url_with_params.com?a=b&c=d"),
                ("label", "=", "label"),
            ],
            [("url", "=", self.base_url + '#')],
            [("url", "=", "https://www.odoo.com?test=%20+3&this=that"), ("label", "=", "THERE > there")],  # lxml unescaped
        ]
        trackers_to_fail = [
            [("url", "=", "https://test_542152qsdqsd.com"), ("label", "ilike", "_")],
            [("url", "ilike", "%mailto:afunemail@somewhere.com")],
            [("label", '=', 'Without href')]
        ]

        for tracker_to_find in trackers_to_find:
            with self.subTest(tracker_to_find=tracker_to_find):
                self.assertTrue(self.env["link.tracker"].search(tracker_to_find))

        for tracker_to_fail in trackers_to_fail:
            with self.subTest(tracker_to_fail=tracker_to_fail):
                self.assertFalse(self.env["link.tracker"].search(tracker_to_fail))

    @mute_logger("odoo.tests.common.requests")
    def test_shorten_links_html_different_labels(self):
        # Covers multiple additions from web_editor's convert_inline.js classToStyle
        content = """<p>There is a <a href="https://www.odoo.com">logo.png</a> here,
<a href="https://www.odoo.com">there</a>, and in this
<a href="https://www.odoo.com"><!--[if mso]><img src="https://www.odoo.com/logo.png" alt="image" style="1"/><![endif]-->
<!--[if !mso]><!--><img src="https://www.odoo.com/logo.png" style="2" alt="image"/><!--<![endif]--></a>
and also <a href="https://www.odoo.com">
    <p class="o_outlook_hack" style="text-align: center; margin: 0px;"><img src="https://www.odoo.com/logo.png" fakealt="image3" alt="image2's trouble"></img></p>
</a>
Single/Nested quotes are not <a href="https://www.odoo.com"><img src='https://www.odoo.com/logo.png' alt='"scary"'/></a>
Nor escaped <a href="https://www.odoo.com">  <img src="https://www.odoo.com/logo.png" alt="ins \' ide"></a>
Nor escaped <a href="https://www.odoo.com"> blurp <img src="https://www.odoo.com/logo.png" alt="ins \' ide"></a>
Without matched label because inside tags are a pain and rare: <a href="https://www.odoo.com"><em>here</em></a>
Without alt, filename is used: <a href="https://www.odoo.com"><img src="https://www.odoo.com/logo.png"></a>
And here is the same: <a href="https://www.odoo.com"><img src="https://www.odoo.com/logo.png"></a></p>"""

        expected_pattern = re.compile(
            rf"""<p>There is a <a href="{self.base_url}/r/(\w+)+">logo.png</a> here,
<a href="{self.base_url}/r/(\w+)+">there</a>, and in this
<a href="{self.base_url}/r/(\w+)+"><!--\[if mso]><img src="https://www.odoo.com/logo.png" alt="image" style="1"/><!\[endif]-->
<!--\[if !mso]><!--><img src="https://www.odoo.com/logo.png" style="2" alt="image"/><!--<!\[endif]--></a>
and also <a href="{self.base_url}/r/(\w+)+">
    <p class="o_outlook_hack" style="text-align: center; margin: 0px;"><img src="https://www.odoo.com/logo.png" fakealt="image3" alt="image2\'s trouble"/></p>
</a>
Single/Nested quotes are not <a href="{self.base_url}/r/(\w+)+"><img src="https://www.odoo.com/logo.png" alt="&quot;scary&quot;"/></a>
Nor escaped <a href="{self.base_url}/r/(\w+)+">  <img src="https://www.odoo.com/logo.png" alt="ins \' ide"/></a>
Nor escaped <a href="{self.base_url}/r/(\w+)+"> blurp <img src="https://www.odoo.com/logo.png" alt="ins \' ide"/></a>
Without matched label because inside tags are a pain and rare: <a href="{self.base_url}/r/(\w+)+"><em>here</em></a>
Without alt, filename is used: <a href="{self.base_url}/r/(\w+)+"><img src="https://www.odoo.com/logo.png"/></a>
And here is the same: <a href="{self.base_url}/r/(\w+)+"><img src="https://www.odoo.com/logo.png"/></a></p>"""
        )

        new_content = self.env["mail.render.mixin"]._shorten_links(content, {})
        self.assertRegex(new_content, expected_pattern)

        trackers_to_find = [
            [("url", "=", "https://www.odoo.com"), ("label", "=", "logo.png")],
            [("url", "=", "https://www.odoo.com"), ("label", "=", "there")],
            [("url", "=", "https://www.odoo.com"), ("label", "=", "[media] image")],
            [("url", "=", "https://www.odoo.com"), ("label", "=", "[media] image2's trouble")],
            [("url", "=", "https://www.odoo.com"), ("label", "=", "blurp")],
            [("url", "=", "https://www.odoo.com"), ("label", "=", '[media] "scary"')],
            [("url", "=", "https://www.odoo.com"), ("label", "=", "[media] ins ' ide")],
            [("url", "=", "https://www.odoo.com"), ("label", "=", False)],
            [("url", "=", "https://www.odoo.com"), ("label", "=", "[media] logo.png")],
        ]
        for tracker_to_find in trackers_to_find:
            with self.subTest(tracker_to_find=tracker_to_find):
                self.assertTrue(
                    self.env["link.tracker"].search(tracker_to_find),
                    f"Tracker labeled {tracker_to_find[1][2]} was not found.",
                )

        link_pattern = re.compile(rf'href="({self.base_url}/r/(\w+)+)"', flags=re.DOTALL)
        matches = link_pattern.findall(new_content)

        def assert_different_shortcode(idx1, idx2):
            self.assertNotEqual(
                matches[idx1][0],
                matches[idx2][0],
                f"Different labels {trackers_to_find[idx1][1][2]} and {trackers_to_find[idx2][1][2]} should have different short codes.",
            )

        # Making sure that no replacement of the wrong line has been performed with the other
        for idx in range(len(trackers_to_find) - 2):
            assert_different_shortcode(idx, idx + 1)
        self.assertNotEqual(matches[0], matches[8])
        self.assertEqual(
            matches[8], matches[9], "Links to the same image without alt should be covered by the same tracker."
        )

    @mute_logger("odoo.tests.common.requests")
    def test_shorten_links_html_including_base_url(self):
        content = f"""<p>
This is a link: <a href="https://www.worldcommunitygrid.org">https://www.worldcommunitygrid.org</a><br/>
This is another: <a href="{self.base_url}/odoo?debug=1&more=2">{self.base_url}</a><br/>
And a third: <a href="{self.base_url}">Here</a>
And a forth: <a href="{self.base_url}">Here</a>
And a fifth: <a href="{self.base_url}">Here too</a>
And a 6th: <a href="/odoo">Here2</a><br>
And a 7th: <a href="{self.base_url}/odoo">Here2</a><br>
And a last, more complex: <a href="https://boinc.berkeley.edu/forum_thread.php?id=14544&postid=106833">There!</a>
</p>"""

        expected_pattern = re.compile(
            rf"""<p>
This is a link: <a href="{self.base_url}/r/(\w+)">https://www.worldcommunitygrid.org</a><br/>
This is another: <a href="{self.base_url}/r/(\w+)">{self.base_url}</a><br/>
And a third: <a href="{self.base_url}/r/(\w+)">Here</a>
And a forth: <a href="{self.base_url}/r/(\w+)">Here</a>
And a fifth: <a href="{self.base_url}/r/(\w+)">Here too</a>
And a 6th: <a href="{self.base_url}/r/(\w+)">Here2</a><br/>
And a 7th: <a href="{self.base_url}/r/(\w+)">Here2</a><br/>
And a last, more complex: <a href="{self.base_url}/r/(\w+)">There!</a>
</p>"""
        )
        new_content = self.env["mail.render.mixin"]._shorten_links(content, {})

        self.assertRegex(new_content, expected_pattern)
        matches = expected_pattern.search(new_content).groups()
        # 3rd and 4th, 6th and 7th lead to the same short_urls
        self.assertEqual(matches[2], matches[3])
        self.assertEqual(matches[5], matches[6])
        # The others not.
        self.assertNotEqual(matches[0], matches[1])
        self.assertNotEqual(matches[0], matches[2])
        self.assertNotEqual(matches[1], matches[2])
        self.assertNotEqual(matches[3], matches[4])
        self.assertNotEqual(matches[4], matches[5])

    @mute_logger("odoo.tests.common.requests")
    def test_shorten_links_html_markup(self):
        content = Markup('<p>A link: <a href="https://www.worldcommunitygrid.org">Link</a></p>')

        new_content = self.env["mail.render.mixin"]._shorten_links(content, {})
        self.assertTrue(isinstance(new_content, Markup))

        expected_pattern = re.compile(rf'<p>A link: <a href="{self.base_url}/r/\w+">Link</a></p>')
        self.assertRegex(new_content, expected_pattern)

    @mute_logger("odoo.tests.common.requests")
    def test_shorten_links_html_skip_shorts(self):
        old_content = self.env["mail.render.mixin"]._shorten_links(
            'This is a link: <a href="https://test_542152qsdqsd.com">old</a>', {})
        created_short_url_match = re.search(TEXT_URL_REGEX, old_content)
        self.assertIsNotNone(created_short_url_match)
        created_short_url = created_short_url_match[0]
        self.assertRegex(created_short_url, "{base_url}/r/[\\w]+".format(base_url=self.base_url))

        new_content = self.env["mail.render.mixin"]._shorten_links(
            f'Reusing this old <a href="{created_short_url}">link</a> with a new <a href="https://odoo.com">one</a>', {}
        )
        expected = re.compile(
            rf'Reusing this old <a href="{created_short_url}">link</a> with a new <a href="{self.base_url}/r/\w+">one</a>'
        )
        self.assertRegex(new_content, expected)

    @mute_logger("odoo.tests.common.requests")
    def test_shorten_links_text_including_base_url(self):
        content = f"""
This is a link: https://www.worldcommunitygrid.org
This is another: {self.base_url}/odoo?debug=1&more=2
A third: {self.base_url}
A forth: {self.base_url}
And a last, with question mark: https://boinc.berkeley.edu/forum_thread.php?id=14544&postid=106833"""

        expected_pattern = re.compile(
            rf"""
This is a link: {self.base_url}/r/\w+
This is another: {self.base_url}/r/\w+
A third: {self.base_url}/r/(\w+)
A forth: {self.base_url}/r/(\w+)
And a last, with question mark: {self.base_url}/r/(\w+)"""
        )
        new_content = self.env["mail.render.mixin"]._shorten_links_text(content, {})

        self.assertRegex(new_content, expected_pattern)
        matches = expected_pattern.search(new_content).groups()
        # 3rd and 4th lead to the same short_url
        self.assertEqual(matches[0], matches[1])

    def test_shorten_links_text_skip_shorts(self):
        old_content = self.env["mail.render.mixin"]._shorten_links_text(
            'This is a link: https://test_542152qsdqsd.com', {})
        created_short_url_match = re.search(TEXT_URL_REGEX, old_content)
        self.assertIsNotNone(created_short_url_match)
        created_short_url = created_short_url_match[0]
        self.assertRegex(created_short_url, rf"{self.base_url}/r/\w+")

        new_content = self.env["mail.render.mixin"]._shorten_links_text(
            f'Reusing this old link {created_short_url} with a new one, https://odoo.com</a>', {}
        )
        expected = re.compile(rf'Reusing this old link {created_short_url} with a new one, {self.base_url}/r/\w+')
        self.assertRegex(new_content, expected)
