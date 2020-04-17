# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestMailRenderMixin(common.TransactionCase):
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
