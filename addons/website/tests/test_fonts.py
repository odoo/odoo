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


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteIconFont(odoo.tests.HttpCase):
    """
    Tests for `website._get_icon_font_family` and the
    `website.icons_fonts_preload` template.

    Only the icon font the website renders with is preloaded, the other Material
    Symbols variants are never fetched by the visitor's browser.
    """

    def setUp(self):
        super().setUp()
        self.website = self.env['website'].browse(self.ref('base.default_website'))

    def _set_icon_font(self, value):
        self.env['website.assets'].with_context(website_id=self.website.id).make_scss_customization(
            '/website/static/src/scss/options/user_values.scss', {'icon-font-family': value})

    def _preloaded_icon_fonts(self):
        head = self.url_open('/').text.partition('</head>')[0]
        return re.findall(r'web\.(material_symbols_\w+)\.min\.woff2', head)

    def _get_icon_font_family(self):
        return self.website.with_context(website_id=self.website.id)._get_icon_font_family()

    def test_default_website_preloads_the_outlined_font(self):
        self.assertFalse(self._get_icon_font_family())
        self.assertEqual(self._preloaded_icon_fonts(), ['material_symbols_outlined'])

    def test_website_preloads_the_selected_font_only(self):
        for variant in ('Rounded', 'Sharp'):
            with self.subTest(variant=variant):
                self._set_icon_font(f"'Material Symbols {variant}'")
                self.assertEqual(self._get_icon_font_family(), f'Material Symbols {variant}')
                self.assertEqual(
                    self._preloaded_icon_fonts(),
                    [f'material_symbols_{variant.lower()}'],
                )


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteThemeGates(odoo.tests.HttpCase):
    """
    Tests for `website._get_theme_gates`: the theme settings that switch CSS
    rules on, rendered on `<html data-o-theme-gates>`.
    """

    def setUp(self):
        super().setUp()
        self.website = self.env['website'].browse(self.ref('base.default_website'))

    def _set_values(self, values):
        self.env['website.assets'].with_context(website_id=self.website.id).make_scss_customization(
            '/website/static/src/scss/options/user_values.scss', values)

    def _get_theme_gates(self):
        return self.website.with_context(website_id=self.website.id)._get_theme_gates().split()

    def test_theme_gates(self):
        # The default header has a shadow, the default palette sets the
        # headings color of two color presets, the buttons are filled, the
        # layout is full.
        default = ['menu-shadow-class', 'o-cc2-headings', 'o-cc5-headings', 'btn-primary-fill', 'btn-secondary-fill', 'layout-full']
        self.assertEqual(self._get_theme_gates(), default)
        self.assertIn(
            f'data-o-theme-gates="{' '.join(default)}"', self.url_open('/').text.partition('<head')[0])

        self._set_values({
            'headings-font-weight-bold': '800',
            'input-border-width': '1px',
            'input-border-bottom-width': '3px',
            # Same as the headings value: not set apart.
            'display-1-margin-top': '0',
        })
        expected = ['headings-font-weight-bold', 'input-border-bottom-width', *default]
        self.assertEqual(self._get_theme_gates(), expected)
        self.assertIn(
            f'data-o-theme-gates="{' '.join(expected)}"',
            self.url_open('/').text.partition('<head')[0],
        )

    def test_color_gates(self):
        self.env['website.assets'].with_context(website_id=self.website.id).make_scss_customization(
            '/website/static/src/scss/options/colors/user_color_palette.scss', {
                'o-cc1-headings': '#123456',
                # A dark header.
                'menu-custom': '#000000',
            })
        self._set_values({'o-cc3-bg-gradient': 'linear-gradient(#FFFFFF, #000000)'})
        self.assertEqual(self._get_theme_gates(), [
            'menu-shadow-class', 'menu-dark',
            'o-cc1-headings', 'o-cc2-headings', 'o-cc3-bg-gradient', 'o-cc5-headings',
            'btn-primary-fill', 'btn-secondary-fill', 'menu-custom', 'layout-full',
        ])
        # A dark palette: dark body background too.
        self._set_values({'color-palettes-name': "'default-dark-1'"})
        self.assertIn('body-dark', self._get_theme_gates())

    def test_style_gates(self):
        self._set_values({
            'btn-primary-flat': 'true',
            'btn-secondary-outline': 'true',
            'link-underline': "'always'",
            'layout': "'postcard'",
        })
        self.assertEqual(self._get_theme_gates()[3:], [
            'btn-primary-fill', 'btn-primary-flat', 'btn-secondary-outline',
            'link-underline-always', 'layout-boxed', 'layout-postcard',
        ])

    def test_area_classes(self):
        # The header and footer color presets are rendered as classes (the
        # CSS doesn't compile them in for those elements).
        classes = self.website.with_context(website_id=self.website.id)._get_theme_area_classes()
        self.assertEqual((classes['menu'], classes['footer']), ('o_cc1', 'o_cc2'))
        page = self.url_open('/').text
        self.assertRegex(page, r'<nav data-name="Navbar"[^>]*class="[^"]* o_cc1 [^"]*" data-o-cc-area="menu"')
        self.assertRegex(page, r'<footer [^>]*class="[^"]* o_cc2 [^"]*" data-o-cc-area="footer"')
        self.env['website.assets'].with_context(website_id=self.website.id).make_scss_customization(
            '/website/static/src/scss/options/colors/user_color_palette.scss', {'menu': '4'})
        self.assertRegex(self.url_open('/').text, r'<nav data-name="Navbar"[^>]*class="[^"]* o_cc4 [^"]*" data-o-cc-area="menu"')
