import re
import unittest
from unittest.mock import patch

import odoo.tests
from odoo.tools.config import config

from odoo.addons.base.models.ir_qweb import IrQweb


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteFontUrls(odoo.tests.HttpCase):
    """
    Tests for `website._get_font_urls` and the `website.font_links` template.

    The fonts used by a website are extracted from a dedicated bundle and emitted
    as `<link rel="stylesheet">`tags in the page `<head>`.
    """

    def setUp(self):
        super().setUp()
        self.website = self.env['website'].browse(self.ref('base.default_website'))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_font_urls(self, website=None):
        website = website or self.website
        return website.with_context(website_id=website.id)._get_font_urls()

    def _set_fonts(self, values, website=None):
        website = website or self.website
        self.env['website.assets'].with_context(website_id=website.id).make_scss_customization(
            '/website/static/src/scss/options/user_values.scss', values)

    def _create_font_attachment(self, font_name):
        return self.env['ir.attachment'].create({
            'name': f'{font_name} (google-font)',
            'type': 'binary',
            'mimetype': 'text/css',
            'raw': b'/* test font css */',
            'public': True,
        })

    # ------------------------------------------------------------------
    # Google fonts
    # ------------------------------------------------------------------

    def test_default_google_fonts(self):
        # The default website uses 'Inter' for the body and 'Inter Tight' for
        # the headings. Each of them should be exported once, as a Google
        # Fonts URL.
        urls = self._get_font_urls()
        self.assertEqual(len(urls), 2, urls)
        self.assertTrue(
            urls[0].startswith('https://fonts.googleapis.com/css?family=Inter:100,100i'),
            urls[0],
        )
        self.assertTrue(
            urls[1].startswith('https://fonts.googleapis.com/css?family=Inter+Tight:100,100i'),
            urls[1],
        )
        for url in urls:
            self.assertTrue(url.endswith('&display=swap&subset=latin,latin-ext,vietnamese'), url)

    def test_same_google_font_for_several_aliases_is_deduplicated(self):
        self._set_fonts({'font': "'Roboto'", 'headings-font': "'Roboto'"})
        urls = self._get_font_urls()
        self.assertEqual(len(urls), 1, urls)
        self.assertIn('family=Roboto:100,100i', urls[0])

    def test_user_added_google_font(self):
        # Fonts added with the "add font" dialog are stored in the
        # 'google-fonts' option.
        self._set_fonts({
            'font': "'Lobster'",
            'headings-font': "'SYSTEM_FONTS'",
            'google-fonts': "('Lobster',)",
        })
        urls = self._get_font_urls()
        self.assertEqual(len(urls), 1, urls)
        self.assertIn('family=Lobster:100,100i', urls[0])

    # ------------------------------------------------------------------
    # Local fonts
    # ------------------------------------------------------------------

    def test_google_font_served_locally(self):
        attachment = self._create_font_attachment('Roboto')
        self._set_fonts({
            'font': "'Roboto'",
            'headings-font': "'SYSTEM_FONTS'",
            'google-local-fonts': f"('Roboto': {attachment.id})",
        })
        self.assertEqual(
            self._get_font_urls(),
            [f'/web/content/{attachment.id}/google-font-Roboto'],
        )

    def test_no_remote_font_returns_no_url(self):
        # SYSTEM_FONTS has no URL and no attachment: nothing to export.
        self._set_fonts({'font': "'SYSTEM_FONTS'", 'headings-font': "'SYSTEM_FONTS'"})
        self.assertEqual(self._get_font_urls(), [])

    # ------------------------------------------------------------------
    # Multi-website and caching
    # ------------------------------------------------------------------

    def test_multi_website_isolation(self):
        website_2 = self.env['website'].create({'name': 'Website 2'})
        self._set_fonts({'font': "'Roboto'", 'headings-font': "'SYSTEM_FONTS'"})
        urls_1 = self._get_font_urls()
        urls_2 = self._get_font_urls(website_2)
        self.assertEqual(len(urls_1), 1, urls_1)
        self.assertIn('family=Roboto:100,100i', urls_1[0])
        self.assertNotEqual(urls_1, urls_2)
        self.assertTrue(any('family=Inter:' in url for url in urls_2), urls_2)

    @unittest.skipIf('xml' in config['dev_mode'], "The assets cache is disabled in dev mode")
    def test_font_urls_are_cached(self):
        # `_get_font_urls` is cached: the bundle should only be compiled once
        # for repeated calls on the same website.
        original = IrQweb._get_asset_bundle
        calls = []

        def _patched_get_asset_bundle(self, *args, **kwargs):
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(IrQweb, '_get_asset_bundle', _patched_get_asset_bundle):
            urls_1 = self._get_font_urls()
            urls_2 = self._get_font_urls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(urls_1, urls_2)

    def test_font_urls_cache_invalidated_on_change(self):
        urls = self._get_font_urls()
        self.assertTrue(any('family=Inter:' in url for url in urls), urls)
        # Customizing the fonts must invalidate the assets cache.
        self._set_fonts({'font': "'Roboto'", 'headings-font': "'SYSTEM_FONTS'"})
        urls = self._get_font_urls()
        self.assertEqual(len(urls), 1, urls)
        self.assertIn('family=Roboto:100,100i', urls[0])

    # ------------------------------------------------------------------
    # Rendered pages
    # ------------------------------------------------------------------

    def test_page_head_contains_font_links(self):
        self._set_fonts({'font': "'Roboto'", 'headings-font': "'Roboto'"})
        self._get_font_urls()
        page = self.url_open('/').text
        self.assertIn('<link rel="preconnect" href="https://fonts.googleapis.com"/>', page)
        font_links = [
            tag for tag in re.findall(r'<link\b[^>]*>', page)
            if 'fonts.googleapis.com/css?family=' in tag
        ]
        self.assertEqual(len(font_links), 1, "One <link> per distinct font is expected")
        self.assertIn('rel="stylesheet"', font_links[0])
        self.assertIn('family=Roboto:100,100i', font_links[0])

    def test_page_head_with_google_served_fonts_contains_preconnect_links(self):
        self._set_fonts({'font': "'Roboto'", 'headings-font': "'Roboto'"})
        self._get_font_urls()
        page = self.url_open('/').text
        self.assertIn('<link rel="preconnect" href="https://fonts.googleapis.com"/>', page)
        self.assertIn('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin=""/>', page)

    def test_page_head_with_locally_served_fonts_does_not_contain_preconnect_links(self):
        attachment = self._create_font_attachment('Roboto')
        self._set_fonts({
            'font': "'Roboto'",
            'headings-font': "'SYSTEM_FONTS'",
            'google-local-fonts': f"('Roboto': {attachment.id})",
        })
        self._get_font_urls()
        page = self.url_open('/').text
        self.assertNotIn('<link rel="preconnect" href="https://fonts.googleapis.com"/>', page)
        self.assertNotIn('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin=""/>', page)
