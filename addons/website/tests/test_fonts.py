import re
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import lxml.html

import odoo.tests
from odoo.tests.common import MockHTTPClient
from odoo.tools.config import config

from odoo.addons.base.models.ir_qweb import IrQweb


def _font_file_url(family, subset, weight=None, style='normal'):
    """URL of the font file served by `_google_css`, the weight is only part of
    the URL for static fonts (a variable font has a single file for all its
    weights)."""
    slug = family.lower()
    suffix = f'-{weight}' if weight else ''
    return f'https://fonts.gstatic.com/s/{slug}/v1/{slug}-{subset}-{style}{suffix}.woff2'


def _google_css(family, subsets=('latin',), weights=(400,), variable=True):
    """Build a stylesheet similar to the one served by Google Fonts: one
    `@font-face` per subset, style and weight, preceded by a comment with the
    name of the subset."""
    blocks = []
    for subset in subsets:
        for style in ('normal', 'italic'):
            for weight in weights:
                url = _font_file_url(family, subset, None if variable else weight, style)
                blocks.append(
                    f"/* {subset} */\n"
                    "@font-face {\n"
                    f"  font-family: '{family}';\n"
                    f"  font-style: {style};\n"
                    f"  font-weight: {weight};\n"
                    "  font-display: swap;\n"
                    f"  src: url({url}) format('woff2');\n"
                    "  unicode-range: U+0000-00FF;\n"
                    "}\n"
                )
    return ''.join(blocks)


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
class TestWebsiteFontPreload(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        self.website = self.env['website'].browse(self.ref('base.default_website'))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_fonts(self, values):
        self.env['website.assets'].with_context(website_id=self.website.id).make_scss_customization(
            '/website/static/src/scss/options/user_values.scss', values)

    def _set_google_fonts(self, font, headings_font=None, **values):
        """Use fonts served by Google, `values` can set the font weights."""
        headings_font = headings_font or font
        self._set_fonts({
            'font': f"'{font}'",
            'headings-font': f"'{headings_font}'",
            'google-fonts': str(tuple({font, headings_font})),
            **values,
        })

    def _mock_google_fonts(self, css_by_family, status=200):
        def get_css(req):
            family = parse_qs(urlsplit(req.url).query)['family'][0].split(':')[0]
            return css_by_family.get(family, '')

        return MockHTTPClient(
            url='https://fonts.googleapis.com/css',
            method='GET',
            return_status=status,
            return_body=get_css,
        )

    def _get_preloads(self, lang=None):
        return self.website.with_context(website_id=self.website.id)._get_font_preloads(lang)

    def _get_preload_urls(self, lang=None):
        return [url for url, _mime_type in self._get_preloads(lang)]

    def _create_local_font_css(self, raw):
        return self.env['ir.attachment'].create({
            'name': 'Local font (google-font)',
            'type': 'binary',
            'mimetype': 'text/css',
            'raw': raw.encode(),
            'public': True,
        })

    def _get_head_links(self, page):
        head = lxml.html.fromstring(page).find('head')
        return list(head.iter('link'))

    def _get_page_preloads(self, page):
        # The icon fonts are preloaded too, but without type: only keep the
        # website fonts.
        return [
            (link.get('href'), link.get('type'), link.get('crossorigin'))
            for link in self._get_head_links(page)
            if link.get('rel') == 'preload'
            and link.get('as') == 'font'
            and link.get('type', '').startswith('font/')
        ]

    # ------------------------------------------------------------------
    # Google fonts
    # ------------------------------------------------------------------

    def test_default_weights(self):
        # Without customization the body uses 400 and the headings use 500.
        self._set_google_fonts('Preloaddef')
        css = _google_css('Preloaddef', weights=(400, 500, 700), variable=False)
        with self._mock_google_fonts({'Preloaddef': css}):
            self.assertEqual(self._get_preloads(), [
                (_font_file_url('Preloaddef', 'latin', 400), 'font/woff2'),
                (_font_file_url('Preloaddef', 'latin', 500), 'font/woff2'),
            ])

    def test_customized_weights(self):
        # Each font is preloaded with the weight used for its role, the italic
        # and the other weights are never preloaded.
        self._set_google_fonts(
            'Preloadstat', 'Preloadhead',
            **{'font-weight-normal': '300', 'headings-font-weight': '700'},
        )
        css = {
            'Preloadstat': _google_css('Preloadstat', weights=(300, 400, 700), variable=False),
            'Preloadhead': _google_css('Preloadhead', weights=(300, 400, 700), variable=False),
        }
        with self._mock_google_fonts(css):
            self.assertEqual(self._get_preload_urls(), [
                _font_file_url('Preloadstat', 'latin', 300),
                _font_file_url('Preloadhead', 'latin', 700),
            ])

    def test_missing_weight_uses_the_closest_one(self):
        self._set_google_fonts('Preloadclose', **{'headings-font-weight': '600'})
        css = _google_css('Preloadclose', weights=(400, 700), variable=False)
        with self._mock_google_fonts({'Preloadclose': css}):
            self.assertEqual(self._get_preload_urls(), [
                _font_file_url('Preloadclose', 'latin', 400),
                _font_file_url('Preloadclose', 'latin', 700),
            ])

    def test_variable_font_is_preloaded_once(self):
        # A single file serves all the weights: no duplicated preload and a
        # single request for the stylesheet.
        self._set_google_fonts('Preloadvar', **{'headings-font-weight': '700'})
        css = _google_css('Preloadvar', weights=(400, 700), variable=True)
        with self._mock_google_fonts({'Preloadvar': css}) as mock:
            self.assertEqual(self._get_preload_urls(), [_font_file_url('Preloadvar', 'latin')])
            mock.assert_called(1)

    def test_stylesheets_are_cached(self):
        self._set_google_fonts('Preloadcache')
        css = _google_css('Preloadcache', weights=(400, 500), variable=True)
        with self._mock_google_fonts({'Preloadcache': css}) as mock:
            urls = self._get_preload_urls()
            self.assertEqual(urls, [_font_file_url('Preloadcache', 'latin')])
            self.assertEqual(self._get_preload_urls(), urls)
            self.assertEqual(self._get_preload_urls('ru_RU'), [], "No cyrillic subset in this font")
            mock.assert_called(1)

    def test_subset_matches_the_language(self):
        # `env.lang` only accepts installed languages.
        self.env['res.lang']._activate_lang('ru_RU')
        self._set_google_fonts('Preloadsub')
        css = _google_css('Preloadsub', subsets=('latin', 'latin-ext', 'cyrillic', 'greek'), weights=(400, 500))
        with self._mock_google_fonts({'Preloadsub': css}):
            for lang, subset in [
                ('en_US', 'latin'),
                ('pl_PL', 'latin'),
                ('ru_RU', 'cyrillic'),
                ('el_GR', 'greek'),
            ]:
                with self.subTest(lang=lang):
                    self.assertEqual(self._get_preload_urls(lang), [_font_file_url('Preloadsub', subset)])
            # By default, the language of the environment is used.
            self.assertEqual(
                self.website.with_context(website_id=self.website.id, lang='ru_RU')._get_font_preloads(),
                [(_font_file_url('Preloadsub', 'cyrillic'), 'font/woff2')],
            )

    def test_language_without_subset_preloads_nothing(self):
        self._set_google_fonts('Preloadcjk')
        css = _google_css('Preloadcjk', subsets=('latin',), weights=(400, 500))
        with self._mock_google_fonts({'Preloadcjk': css}) as mock:
            self.assertEqual(self._get_preloads('ja_JP'), [])
            mock.assert_called(0)

    def test_unreachable_google_fonts_preload_nothing(self):
        self._set_google_fonts('Preloadfail')
        with self._mock_google_fonts({}, status=500) as mock:
            self.assertEqual(self._get_preloads(), [])
            # The failure is cached too, Google is not requested again for every page.
            self.assertEqual(self._get_preloads(), [])
            mock.assert_called(1)
            page = self.url_open('/')
            self.assertEqual(page.status_code, 200)
            self.assertEqual(self._get_page_preloads(page.text), [])

    def test_system_fonts_preload_nothing(self):
        self._set_fonts({'font': "'SYSTEM_FONTS'", 'headings-font': "'SYSTEM_FONTS'"})
        with self._mock_google_fonts({}) as mock:
            self.assertEqual(self._get_preloads(), [])
            mock.assert_called(0)

    # ------------------------------------------------------------------
    # Local fonts
    # ------------------------------------------------------------------

    def test_google_font_served_locally(self):
        css = ''.join(
            f"/* {subset} */\n"
            "@font-face {\n"
            "  font-family: 'Preloadlocal';\n"
            "  font-style: normal;\n"
            f"  font-weight: {weight};\n"
            f"  src: url(/web/content/9001/s-preloadlocal-v1-{subset}-{weight}.woff2) format('woff2');\n"
            "}\n"
            for subset in ('latin', 'cyrillic')
            for weight in (400, 500, 700)
        )
        attachment = self._create_local_font_css(css)
        self._set_fonts({
            'font': "'Preloadlocal'",
            'headings-font': "'Preloadlocal'",
            'headings-font-weight': '700',
            'google-local-fonts': f"('Preloadlocal': {attachment.id})",
        })
        # No request is needed to read the stylesheet of a font served locally.
        with self._mock_google_fonts({}) as mock:
            self.assertEqual(self._get_preloads(), [
                ('/web/content/9001/s-preloadlocal-v1-latin-400.woff2', 'font/woff2'),
                ('/web/content/9001/s-preloadlocal-v1-latin-700.woff2', 'font/woff2'),
            ])
            self.assertEqual(self._get_preload_urls('ru_RU'), [
                '/web/content/9001/s-preloadlocal-v1-cyrillic-400.woff2',
                '/web/content/9001/s-preloadlocal-v1-cyrillic-700.woff2',
            ])
            mock.assert_called(0)

    def test_uploaded_font_without_subset(self):
        css = (
            "@font-face{font-family: 'Preloadupload'; font-style: normal; font-weight: 400;"
            " font-display: swap; src:url(\"/web/content/9002/Preloadupload-Regular.ttf\");}"
            "@font-face{font-family: 'Preloadupload'; font-style: italic; font-weight: 400;"
            " font-display: swap; src:url(\"/web/content/9003/Preloadupload-Italic.ttf\");}"
        )
        attachment = self._create_local_font_css(css)
        self._set_fonts({
            'font': "'Preloadupload'",
            'headings-font': "'SYSTEM_FONTS'",
            'uploaded-local-fonts': f"('Preloadupload': {attachment.id})",
        })
        self.assertEqual(self._get_preloads('fr_FR'), [('/web/content/9002/Preloadupload-Regular.ttf', 'font/ttf')])
        self.assertEqual(self._get_preloads('ru_RU'), [('/web/content/9002/Preloadupload-Regular.ttf', 'font/ttf')])

    def test_private_or_missing_local_stylesheet_preloads_nothing(self):
        attachment = self._create_local_font_css(
            "@font-face{font-family: 'Preloadprivate'; src:url(/web/content/9004/a.woff2) format('woff2');}")
        attachment.public = False
        self._set_fonts({
            'font': "'Preloadprivate'",
            'headings-font': "'SYSTEM_FONTS'",
            'google-local-fonts': f"('Preloadprivate': {attachment.id})",
        })
        self.assertEqual(self._get_preloads(), [])

    # ------------------------------------------------------------------
    # Rendered pages
    # ------------------------------------------------------------------

    def test_page_head_contains_font_preloads(self):
        self._set_google_fonts('Preloadpage', 'Preloadpagehead')
        css = {
            'Preloadpage': _google_css('Preloadpage', weights=(400, 500), variable=True),
            'Preloadpagehead': _google_css('Preloadpagehead', weights=(400, 500), variable=True),
        }
        with self._mock_google_fonts(css):
            page = self.url_open('/').text
        self.assertEqual(self._get_page_preloads(page), [
            (_font_file_url('Preloadpage', 'latin'), 'font/woff2', ''),
            (_font_file_url('Preloadpagehead', 'latin'), 'font/woff2', ''),
        ])
        # The files are requested after the connection to their server is
        # opened and before the stylesheets declaring them.
        kinds = [
            link.get('rel')
            for link in self._get_head_links(page)
            if 'fonts.g' in link.get('href', '')
        ]
        self.assertEqual(kinds, ['preconnect', 'preconnect', 'preload', 'preload', 'stylesheet', 'stylesheet'])

    def test_page_preloads_the_subset_of_the_language(self):
        lang_ru = self.env['res.lang']._activate_lang('ru_RU')
        lang_ru.write({'url_code': 'ru'})
        self.website.language_ids = self.env.ref('base.lang_en') + lang_ru
        self.website.default_lang_id = self.env.ref('base.lang_en')
        self._set_google_fonts('Preloadlang')
        css = _google_css('Preloadlang', subsets=('latin', 'cyrillic'), weights=(400, 500), variable=True)
        with self._mock_google_fonts({'Preloadlang': css}):
            en_page = self.url_open('/').text
            ru_page = self.url_open('/ru').text
        self.assertEqual(
            self._get_page_preloads(en_page),
            [(_font_file_url('Preloadlang', 'latin'), 'font/woff2', '')],
        )
        self.assertEqual(
            self._get_page_preloads(ru_page),
            [(_font_file_url('Preloadlang', 'cyrillic'), 'font/woff2', '')],
        )

    def test_page_head_without_remote_font_has_no_preload(self):
        self._set_fonts({'font': "'SYSTEM_FONTS'", 'headings-font': "'SYSTEM_FONTS'"})
        page = self.url_open('/').text
        self.assertEqual(self._get_page_preloads(page), [])


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
