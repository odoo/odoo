import re
import unittest
from unittest.mock import Mock, patch

import lxml.html

import odoo.tests
from odoo.tests.common import MockHTTPClient
from odoo.tools.config import config

from odoo.addons.base.models.ir_qweb import IrQweb


def _font_file_url(family, subset, weight=None, style='normal'):
    """URL of the font file declared by `_font_css`, the weight is only part of
    the URL for static fonts (a variable font has a single file for all its
    weights)."""
    slug = family.lower()
    suffix = f'-{weight}' if weight else ''
    return f'/web/content/preload/{slug}-{subset}-{style}{suffix}.woff2'


def _font_css(family, subsets=('latin',), weights=(400,), variable=True):
    """Build a stylesheet similar to the one of a Google font served locally:
    one `@font-face` per subset, style and weight, preceded by a comment with
    the name of the subset."""
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


# The latin files of the default fonts (Inter and Inter Tight, variable fonts
# shipped in the module) for the body and the headings.
DEFAULT_FONT_PRELOADS = [
    ('/website/static/fonts/Inter/inter-latin-normal-100-900.woff2', 'font/woff2'),
    ('/website/static/fonts/Inter_Tight/inter-tight-latin-normal-100-900.woff2', 'font/woff2'),
]


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

    def _set_google_font(self, font, headings_font=None, website=None):
        """Use a font served by Google (the theme fonts are shipped in the code,
        a font added with the "add font" dialog is served by Google)."""
        self._set_fonts({
            'font': f"'{font}'",
            'headings-font': f"'{headings_font or font}'",
            'google-fonts': f"('{font}',)",
        }, website)

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

    def test_default_fonts_are_served_locally(self):
        # The default website uses 'Inter' for the body and 'Inter Tight' for
        # the headings. Each of them should be exported once, as the URL of
        # its stylesheet shipped in the module.
        self.assertEqual(self._get_font_urls(), [
            '/website/static/fonts/Inter/Inter.css',
            '/website/static/fonts/Inter_Tight/Inter_Tight.css',
        ])

    def test_same_google_font_for_several_aliases_is_deduplicated(self):
        self._set_google_font('Lobster')
        urls = self._get_font_urls()
        self.assertEqual(len(urls), 1, urls)
        self.assertIn('family=Lobster:100,100i', urls[0])

    def test_same_local_font_for_several_aliases_is_deduplicated(self):
        self._set_fonts({'font': "'Roboto'", 'headings-font': "'Roboto'"})
        self.assertEqual(self._get_font_urls(), ['/website/static/fonts/Roboto/Roboto.css'])

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
        self.assertTrue(urls[0].endswith('&display=swap&subset=latin,latin-ext,vietnamese'), urls[0])

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
        # The checksum of the stylesheet busts the browser cache.
        self.assertEqual(
            self._get_font_urls(),
            [f'/web/content/{attachment.id}/google-font-Roboto?unique={attachment.checksum}'],
        )

    def test_google_font_made_local_stores_each_file_once(self):
        # A variable font lists the same file for every weight: download and
        # store it once, else browsers fetch the same file once per weight.
        # Like Montserrat: 5 subsets x 2 styles x 9 weights = 90 src, 10 files.
        font_faces = ''.join(
            f"/* {subset} */\n@font-face {{\n  font-family: 'Montserrat';\n"
            f"  font-style: {style};\n  font-weight: {weight};\n"
            f"  src: url(https://fonts.gstatic.com/s/montserrat/v31/{subset}-{style}.woff2) format('woff2');\n}}\n"
            for style in ('normal', 'italic')
            for weight in range(100, 1000, 100)
            for subset in ('cyrillic-ext', 'cyrillic', 'vietnamese', 'latin-ext', 'latin')
        )
        requested = []

        def fake_get(url, **kwargs):
            requested.append(url)
            return Mock(content=font_faces.encode() if 'fonts.googleapis.com' in url else url.encode())

        with patch('requests.Session.get', side_effect=fake_get):
            self._set_fonts({'google-local-fonts': "('Montserrat': '')"})

        css = self.env['ir.attachment'].search([('name', '=', 'Montserrat (google-font)')])
        files = self.env['ir.attachment'].search([('original_id', '=', css.id)])
        src_ids = re.findall(r'/web/content/(\d+)/', css.raw.decode())
        self.assertEqual(len(src_ids), 90)
        self.assertEqual(len(files), 10)
        self.assertEqual(len(requested), 11)  # 1 request for the CSS, 10 for the font files
        self.assertEqual(set(src_ids), {str(file_id) for file_id in files.ids})

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
        self.assertEqual(urls_1, ['/website/static/fonts/Roboto/Roboto.css'])
        self.assertIn('/website/static/fonts/Inter/Inter.css', urls_2)

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
        self.assertIn('/website/static/fonts/Inter/Inter.css', urls)
        # Customizing the fonts must invalidate the assets cache.
        self._set_fonts({'font': "'Roboto'", 'headings-font': "'SYSTEM_FONTS'"})
        self.assertEqual(self._get_font_urls(), ['/website/static/fonts/Roboto/Roboto.css'])

    # ------------------------------------------------------------------
    # Rendered pages
    # ------------------------------------------------------------------

    def test_page_head_contains_font_links(self):
        self._set_google_font('Lobster')
        self._get_font_urls()
        page = self.url_open('/').text
        self.assertIn('<link rel="preconnect" href="https://fonts.googleapis.com"/>', page)
        font_links = [
            tag for tag in re.findall(r'<link\b[^>]*>', page)
            if 'fonts.googleapis.com/css?family=' in tag
        ]
        self.assertEqual(len(font_links), 1, "One <link> per distinct font is expected")
        self.assertIn('rel="stylesheet"', font_links[0])
        self.assertIn('family=Lobster:100,100i', font_links[0])

    def test_page_head_with_google_served_fonts_contains_preconnect_links(self):
        self._set_google_font('Lobster')
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
    """Only the files of the local fonts (stored in attachments or shipped in
    the code) are preloaded: the fonts served by Google are not."""

    def setUp(self):
        super().setUp()
        self.website = self.env['website'].browse(self.ref('base.default_website'))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_fonts(self, values):
        self.env['website.assets'].with_context(website_id=self.website.id).make_scss_customization(
            '/website/static/src/scss/options/user_values.scss', values)

    def _set_local_fonts(self, css_by_family, font, headings_font=None, **values):
        """Use Google fonts served locally, whose stylesheets are given by
        `css_by_family`, `values` can set the font weights."""
        local_fonts = ', '.join(
            f"'{family}': {self._create_local_font_css(css).id}"
            for family, css in css_by_family.items()
        )
        self._set_fonts({
            'font': f"'{font}'",
            'headings-font': f"'{headings_font or font}'",
            'google-local-fonts': f"({local_fonts})",
            **values,
        })

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

    def test_google_fonts_are_not_preloaded(self):
        with MockHTTPClient(url='https://fonts.googleapis.com/css', method='GET') as mock:
            self._set_fonts({
                'font': "'Lobster'",
                'headings-font': "'Lobster'",
                'google-fonts': "('Lobster',)",
            })
            self.assertEqual(self._get_preloads(), [])
            page = self.url_open('/').text
            mock.assert_called(0)
        self.assertEqual(self._get_page_preloads(page), [])

    # ------------------------------------------------------------------
    # Google fonts served locally
    # ------------------------------------------------------------------

    def test_default_weights(self):
        # Without customization the body uses 400 and the headings use 500.
        css = _font_css('Preloaddef', weights=(400, 500, 700), variable=False)
        self._set_local_fonts({'Preloaddef': css}, 'Preloaddef')
        self.assertEqual(self._get_preloads(), [
            (_font_file_url('Preloaddef', 'latin', 400), 'font/woff2'),
            (_font_file_url('Preloaddef', 'latin', 500), 'font/woff2'),
        ])

    def test_customized_weights(self):
        # Each font is preloaded with the weight used for its role, the italic
        # and the other weights are never preloaded.
        css = {
            'Preloadstat': _font_css('Preloadstat', weights=(300, 400, 700), variable=False),
            'Preloadhead': _font_css('Preloadhead', weights=(300, 400, 700), variable=False),
        }
        self._set_local_fonts(
            css, 'Preloadstat', 'Preloadhead',
            **{'font-weight-normal': '300', 'headings-font-weight': '700'},
        )
        self.assertEqual(self._get_preload_urls(), [
            _font_file_url('Preloadstat', 'latin', 300),
            _font_file_url('Preloadhead', 'latin', 700),
        ])

    def test_customized_weight_alone_updates_preloads(self):
        css = _font_css('Preloadweight', weights=(400, 500, 700), variable=False)
        self._set_local_fonts({'Preloadweight': css}, 'Preloadweight')
        self.assertEqual(self._get_preload_urls(), [
            _font_file_url('Preloadweight', 'latin', 400),
            _font_file_url('Preloadweight', 'latin', 500),
        ])
        self._set_fonts({'headings-font-weight': '700'})
        self.assertEqual(self._get_preload_urls(), [
            _font_file_url('Preloadweight', 'latin', 400),
            _font_file_url('Preloadweight', 'latin', 700),
        ])

    def test_missing_weight_uses_the_closest_one(self):
        css = _font_css('Preloadclose', weights=(400, 700), variable=False)
        self._set_local_fonts({'Preloadclose': css}, 'Preloadclose', **{'headings-font-weight': '600'})
        self.assertEqual(self._get_preload_urls(), [
            _font_file_url('Preloadclose', 'latin', 400),
            _font_file_url('Preloadclose', 'latin', 700),
        ])

    def test_variable_font_is_preloaded_once(self):
        # A single file serves all the weights: no duplicated preload.
        css = _font_css('Preloadvar', weights=(400, 700), variable=True)
        self._set_local_fonts({'Preloadvar': css}, 'Preloadvar', **{'headings-font-weight': '700'})
        self.assertEqual(self._get_preload_urls(), [_font_file_url('Preloadvar', 'latin')])

    def test_subset_matches_the_language(self):
        self.env['res.lang']._activate_lang('ru_RU')
        css = _font_css('Preloadsub', subsets=('latin', 'latin-ext', 'cyrillic', 'greek'), weights=(400, 500))
        self._set_local_fonts({'Preloadsub': css}, 'Preloadsub')
        for lang, subset in [
            ('en_US', 'latin'),
            ('pl_PL', 'latin'),
            ('ru_RU', 'cyrillic'),
            ('el_GR', 'greek'),
        ]:
            with self.subTest(lang=lang):
                self.assertEqual(self._get_preload_urls(lang), [_font_file_url('Preloadsub', subset)])
        self.assertEqual(
            self.website.with_context(website_id=self.website.id, lang='ru_RU')._get_font_preloads(),
            [(_font_file_url('Preloadsub', 'cyrillic'), 'font/woff2')],
        )
        self.assertEqual(self._get_preloads('ar_SY'), [], "No arabic subset in this font")

    def test_language_without_subset_preloads_nothing(self):
        css = _font_css('Preloadcjk', subsets=('latin',), weights=(400, 500))
        self._set_local_fonts({'Preloadcjk': css}, 'Preloadcjk')
        self.assertEqual(self._get_preloads('ja_JP'), [])

    def test_system_fonts_preload_nothing(self):
        self._set_fonts({'font': "'SYSTEM_FONTS'", 'headings-font': "'SYSTEM_FONTS'"})
        self.assertEqual(self._get_preloads(), [])

    def test_uploaded_font_without_subset(self):
        css = (
            "@font-face{font-family: 'Preloadupload'; font-style: normal; font-weight: 400;"
            " font-display: swap; src:url(\"/web/font/9002/Preloadupload-Regular.ttf\");}"
            "@font-face{font-family: 'Preloadupload'; font-style: italic; font-weight: 400;"
            " font-display: swap; src:url(\"/web/font/9003/Preloadupload-Italic.ttf\");}"
        )
        attachment = self._create_local_font_css(css)
        self._set_fonts({
            'font': "'Preloadupload'",
            'headings-font': "'SYSTEM_FONTS'",
            'uploaded-local-fonts': f"('Preloadupload': {attachment.id})",
        })
        self.assertEqual(self._get_preloads('fr_FR'), [('/web/font/9002/Preloadupload-Regular.ttf', 'font/ttf')])
        self.assertEqual(self._get_preloads('ru_RU'), [('/web/font/9002/Preloadupload-Regular.ttf', 'font/ttf')])

    def test_uploaded_font_without_extension_has_no_type(self):
        css = "@font-face{font-family: 'Preloadnoext'; font-weight: 400; src:url(\"/web/font/9005/Preloadnoext\");}"
        attachment = self._create_local_font_css(css)
        self._set_fonts({
            'font': "'Preloadnoext'",
            'headings-font': "'SYSTEM_FONTS'",
            'uploaded-local-fonts': f"('Preloadnoext': {attachment.id})",
        })
        self.assertEqual(self._get_preloads(), [('/web/font/9005/Preloadnoext', None)])

    def test_private_local_stylesheet_preloads_nothing(self):
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
    # Default local fonts (shipped in the code)
    # ------------------------------------------------------------------

    def _add_default_local_font(self):
        """Make the `Testlocal` font, whose stylesheet and files are in the
        static directory of the module, available to the website."""
        self.env['ir.asset'].create({
            'name': 'Test default local font',
            'bundle': 'web._assets_primary_variables',
            'directive': 'after',
            'target': 'website/static/src/scss/primary_variables.scss',
            'path': 'website/static/tests/fonts/default_local_font.scss',
        })
        self.env.transaction.invalidate_ormcache('assets')

    def test_new_website_preloads_default_fonts(self):
        website = self.env['website'].create({'name': 'Font preload website'})
        self.assertEqual(website.with_context(website_id=website.id)._get_font_preloads('en_US'), DEFAULT_FONT_PRELOADS)

    def test_default_local_font(self):
        self._add_default_local_font()
        self._set_fonts({
            'font': "'Testlocal'",
            'headings-font': "'Testlocal'",
            'headings-font-weight': '700',
        })
        css_url = '/website/static/tests/fonts/Testlocal/Testlocal.css'
        self.assertEqual(self.website.with_context(website_id=self.website.id)._get_font_urls(), [css_url])
        # The font files are referenced relatively to the stylesheet.
        self.assertEqual(self._get_preloads(), [
            ('/website/static/tests/fonts/Testlocal/Testlocal-latin-normal-400.woff2', 'font/woff2'),
            ('/website/static/tests/fonts/Testlocal/Testlocal-latin-normal-700.woff2', 'font/woff2'),
        ])
        self.assertEqual(self._get_preload_urls('ru_RU'), [
            '/website/static/tests/fonts/Testlocal/Testlocal-cyrillic-normal-400.woff2',
            '/website/static/tests/fonts/Testlocal/Testlocal-cyrillic-normal-700.woff2',
        ])
        page = self.url_open('/').text
        self.assertIn(css_url, [link.get('href') for link in self._get_head_links(page) if link.get('rel') == 'stylesheet'])
        self.assertEqual(self._get_page_preloads(page), [
            ('/website/static/tests/fonts/Testlocal/Testlocal-latin-normal-400.woff2', 'font/woff2', ''),
            ('/website/static/tests/fonts/Testlocal/Testlocal-latin-normal-700.woff2', 'font/woff2', ''),
        ])

    def test_stylesheet_outside_static_directories_is_not_read(self):
        Website = self.env['website']
        self.assertTrue(Website._get_font_faces('/website/static/tests/fonts/Testlocal/Testlocal.css'))
        for css_url in (
            '/website/static/tests/fonts/../../../models/website.css',
            '/website/models/website.py',
            '/website/static/tests/fonts/default_local_font.scss',
            '/website/static/tests/fonts/Testlocal/missing.css',
            'https://fonts.googleapis.com/css?family=Lobster',
        ):
            self.assertEqual(Website._get_font_faces(css_url), {}, css_url)

    # ------------------------------------------------------------------
    # Rendered pages
    # ------------------------------------------------------------------

    def test_page_head_contains_font_preloads(self):
        css = {
            'Preloadpage': _font_css('Preloadpage', weights=(400, 500), variable=True),
            'Preloadpagehead': _font_css('Preloadpagehead', weights=(400, 500), variable=True),
        }
        self._set_local_fonts(css, 'Preloadpage', 'Preloadpagehead')
        page = self.url_open('/').text
        self.assertEqual(self._get_page_preloads(page), [
            (_font_file_url('Preloadpage', 'latin'), 'font/woff2', ''),
            (_font_file_url('Preloadpagehead', 'latin'), 'font/woff2', ''),
        ])
        # The files are requested before the stylesheets declaring them.
        kinds = [
            link.get('rel')
            for link in self._get_head_links(page)
            if 'preload' in link.get('href', '') or 'google-font' in link.get('href', '')
        ]
        self.assertEqual(kinds, ['preload', 'preload', 'stylesheet', 'stylesheet'])

    def test_page_preloads_the_subset_of_the_language(self):
        lang_ru = self.env['res.lang']._activate_lang('ru_RU')
        lang_ru.write({'url_code': 'ru'})
        self.website.language_ids = self.env.ref('base.lang_en') + lang_ru
        self.website.default_lang_id = self.env.ref('base.lang_en')
        css = _font_css('Preloadlang', subsets=('latin', 'cyrillic'), weights=(400, 500), variable=True)
        self._set_local_fonts({'Preloadlang': css}, 'Preloadlang')
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

    def test_page_head_without_font_has_no_preload(self):
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
