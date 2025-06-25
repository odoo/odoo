# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from lxml import etree
from unittest.mock import patch

from odoo.tests import common


class MockLinkTracker(common.BaseCase):

    def setUp(self):
        super(MockLinkTracker, self).setUp()

        def _get_title_from_url(url):
            return "Test_TITLE"

        link_tracker_title_patch = patch('odoo.addons.link_tracker.models.link_tracker.LinkTracker._get_title_from_url', wraps=_get_title_from_url)
        self.startPatcher(link_tracker_title_patch)

    def _get_href_from_anchor_id(self, body, anchor_id):
        """ Parse en html body to find the href of an element given its ID. """
        html = etree.fromstring(body, parser=etree.HTMLParser())
        return html.xpath("//*[@id='%s']" % anchor_id)[0].attrib.get('href')

    def _get_code_from_short_url(self, short_url):
        return self.env['link.tracker.code'].sudo().search([
            ('code', '=', short_url.split('/r/')[-1])
        ])

    def _get_tracker_from_short_url(self, short_url):
        return self._get_code_from_short_url(short_url).link_id

    def assertLinkShortenedHtml(self, body, link_info, link_params=None):
        """ Find shortened links in an HTML content. Usage :

        self.assertLinkShortenedHtml(
            message.body,
            ('url0', 'http://www.odoo.com',  True),
            {'utm_campaign': self.utm_c.name, 'utm_medium': self.utm_m.name}
        )
        """
        (anchor_id, url, is_shortened) = link_info
        anchor_href = self._get_href_from_anchor_id(body, anchor_id)
        if is_shortened:
            self.assertTrue('/r/' in anchor_href, '%s should be shortened: %s' % (anchor_id, anchor_href))
            link_tracker = self._get_tracker_from_short_url(anchor_href)
            self.assertEqual(url, link_tracker.url)
            self.assertLinkParams(url, link_tracker, link_params=link_params)
        else:
            self.assertTrue('/r/' not in anchor_href, '%s should not be shortened: %s' % (anchor_id, anchor_href))
            self.assertEqual(anchor_href, url)

    def assertLinkShortenedText(self, body, link_info, link_params=None):
        """ Find shortened links in an text content. Usage :

        self.assertLinkShortenedText(
            message.body,
            ('http://www.odoo.com',  True),
            {'utm_campaign': self.utm_c.name, 'utm_medium': self.utm_m.name}
        )
        """
        (url, is_shortened) = link_info
        link_tracker = self.env['link.tracker'].search([('url', '=', url)])
        if is_shortened:
            self.assertEqual(len(link_tracker), 1)
            self.assertIn(link_tracker.short_url, body, '%s should be shortened' % (url))
            self.assertLinkParams(url, link_tracker, link_params=link_params)
        else:
            self.assertEqual(len(link_tracker), 0)
            self.assertIn(url, body)

    def assertLinkParams(self, url, link_tracker, link_params=None):
        """ Usage

        self.assertLinkTracker(
            'http://www.example.com',
            link_tracker,
            {'utm_campaign': self.utm_c.name, 'utm_medium': self.utm_m.name}
        )
        """
        # check UTMS are correctly set on redirect URL
        original_url = werkzeug.urls.url_parse(url)
        redirect_url = werkzeug.urls.url_parse(link_tracker.redirected_url)
        redirect_params = redirect_url.decode_query().to_dict(flat=True)
        self.assertEqual(redirect_url.scheme, original_url.scheme)
        self.assertEqual(redirect_url.decode_netloc(), original_url.decode_netloc())
        self.assertEqual(redirect_url.path, original_url.path)
        if link_params:
            self.assertEqual(redirect_params, link_params)
