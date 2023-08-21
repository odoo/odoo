# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo.tests import common, tagged
from odoo.tools import TEXT_URL_REGEX


@tagged('-at_install', 'post_install')
class TestMailRenderMixin(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_url = cls.env["mail.render.mixin"].get_base_url()

    def setUp(self):
        super().setUp()
        r = self.patch_requests()
        r.side_effect=NotImplementedError

    def test_shorten_links(self):
        test_links = [
            '<a href="https://gitlab.com" title="title" fake="fake">test_label</a>',
            '<a href="https://test_542152qsdqsd.com"/>',
            """<a href="https://third_test_54212.com">
                    <img src="imagesrc"/>
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
        ]

        self.env["mail.render.mixin"]._shorten_links("".join(test_links), {})

        trackers_to_find = [
            [("url", "=", "https://gitlab.com"), ("label", "=", "test_label")],
            [("url", "=", "https://test_542152qsdqsd.com")],
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
        ]
        trackers_to_fail = [
            [("url", "=", "https://test_542152qsdqsd.com"), ("label", "ilike", "_")]
        ]

        for tracker_to_find in trackers_to_find:
            self.assertTrue(self.env["link.tracker"].search(tracker_to_find))

        for tracker_to_fail in trackers_to_fail:
            self.assertFalse(self.env["link.tracker"].search(tracker_to_fail))

    def test_shorten_links_html_skip_shorts(self):
        old_content = self.env["mail.render.mixin"]._shorten_links(
            'This is a link: <a href="https://test_542152qsdqsd.com">old</a>', {})
        created_short_url_match = re.search(TEXT_URL_REGEX, old_content)
        self.assertIsNotNone(created_short_url_match)
        created_short_url = created_short_url_match[0]
        self.assertRegex(created_short_url, "{base_url}/r/[\\w]+".format(base_url=self.base_url))

        new_content = self.env["mail.render.mixin"]._shorten_links(
            'Reusing this old <a href="{old_short_url}">link</a> with a new <a href="https://odoo.com">one</a>'
            .format(old_short_url=created_short_url),
            {}
        )
        expected = re.compile(
            'Reusing this old <a href="{old_short_url}">link</a> with a new <a href="{base_url}/r/[\\w]+">one</a>'
            .format(old_short_url=created_short_url, base_url=self.base_url)
        )
        self.assertRegex(new_content, expected)

    def test_shorten_links_html_including_base_url(self):
        content = (
            'This is a link: <a href="https://www.worldcommunitygrid.org">https://www.worldcommunitygrid.org</a><br/>\n'
            'This is another: <a href="{base_url}/web#debug=1&more=2">{base_url}</a><br/>\n'
            'And a third: <a href="{base_url}">Here</a>\n'
            'And a forth: <a href="{base_url}">Here</a>\n'
            'And a fifth: <a href="{base_url}">Here too</a>\n'
            'And a last, more complex: <a href="https://boinc.berkeley.edu/forum_thread.php?id=14544&postid=106833">There!</a>'
            .format(base_url=self.base_url)
        )
        expected_pattern = re.compile(
            'This is a link: <a href="{base_url}/r/[\\w]+">https://www.worldcommunitygrid.org</a><br/>\n'
            'This is another: <a href="{base_url}/r/[\\w]+">{base_url}</a><br/>\n'
            'And a third: <a href="{base_url}/r/([\\w]+)">Here</a>\n'
            'And a forth: <a href="{base_url}/r/([\\w]+)">Here</a>\n'
            'And a fifth: <a href="{base_url}/r/([\\w]+)">Here too</a>\n'
            'And a last, more complex: <a href="{base_url}/r/([\\w]+)">There!</a>'
            .format(base_url=self.base_url)
        )
        new_content = self.env["mail.render.mixin"]._shorten_links(content, {})

        self.assertRegex(new_content, expected_pattern)
        matches = expected_pattern.search(new_content).groups()
        # 3rd and 4th lead to the same short_url
        self.assertEqual(matches[0], matches[1])
        # 5th has different label but should currently lead to the same link
        self.assertEqual(matches[1], matches[2])

    def test_shorten_links_text_including_base_url(self):
        content = (
            'This is a link: https://www.worldcommunitygrid.org\n'
            'This is another: {base_url}/web#debug=1&more=2\n'
            'A third: {base_url}\n'
            'A forth: {base_url}\n'
            'And a last, with question mark: https://boinc.berkeley.edu/forum_thread.php?id=14544&postid=106833'
            .format(base_url=self.base_url)
        )
        expected_pattern = re.compile(
            'This is a link: {base_url}/r/[\\w]+\n'
            'This is another: {base_url}/r/[\\w]+\n'
            'A third: {base_url}/r/([\\w]+)\n'
            'A forth: {base_url}/r/([\\w]+)\n'
            'And a last, with question mark: {base_url}/r/([\\w]+)'
            .format(base_url=self.base_url)
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
        self.assertRegex(created_short_url, "{base_url}/r/[\\w]+".format(base_url=self.base_url))

        new_content = self.env["mail.render.mixin"]._shorten_links_text(
            'Reusing this old link {old_short_url} with a new one, https://odoo.com</a>'
            .format(old_short_url=created_short_url),
            {}
        )
        expected = re.compile(
            'Reusing this old link {old_short_url} with a new one, {base_url}/r/[\\w]+'
            .format(old_short_url=created_short_url, base_url=self.base_url)
        )
        self.assertRegex(new_content, expected)
