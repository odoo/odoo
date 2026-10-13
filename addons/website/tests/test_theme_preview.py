import json
import re

from lxml import html

import odoo.tests
from odoo.tests.common import new_test_user

from odoo.addons.website import color_system as cs


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
        self.assertEqual(set(self._get_theme_gates()), {
            'menu-shadow-class', 'o-cc2-headings', 'o-cc5-headings',
            'btn-primary-fill', 'btn-primary-flat', 'btn-secondary-outline',
            'link-underline-always', 'layout-boxed', 'layout-postcard',
        })


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteThemeComputedColors(odoo.tests.HttpCase):
    """
    Tests for `/website/theme_computed_colors`: the colors the builder
    previews are the ones the compile prints.
    """

    def test_computed_colors_match_the_compile(self):
        website = self.env['website'].browse(self.ref('base.default_website'))
        # The scroll-to-top button's colors are printed only with it.
        self.env['website.assets'].with_context(website_id=website.id).make_scss_customization(
            '/website/static/src/scss/options/user_values.scss', {'footer-scrolltop': 'true'})
        env = website.with_context(website_id=website.id).env
        bundle = env['ir.qweb']._get_asset_bundle(
            'web.assets_frontend', js=False, assets_params=env['ir.asset']._get_asset_params())
        css = bundle.preprocess_css()
        self.assertFalse(bundle.css_errors)
        root = {}
        for selectors, block in re.findall(r'([^{}]+)\{([^{}]*)\}', re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)):
            if ':root' in (selector.strip() for selector in selectors.split(',')):
                root.update((name, value.strip()) for name, value in re.findall(r'--([\w-]+):([^;]*)', block))

        # The values as the page reads them: `var()` substituted.
        var_re = re.compile(r'var\(--([\w-]+)(?:,\s*((?:[^()]|\([^()]*\))*))?\)')

        def resolve(value):
            while (substituted := var_re.sub(lambda match: root.get(match[1], match[2] or ''), value)) != value:
                value = substituted
            return value.strip()

        root = {name: resolve(value) for name, value in root.items()}

        # The inputs as the builder sends them (see `getComputedColorsInputs`).
        user_keys = set(root['o-user-color-keys'].strip('\'"').split())
        is_set = lambda name: name in user_keys or bool(root.get(f'o-default-{name}'))  # noqa: E731
        names = [*cs.GRAYS, *cs.THEME_COLORS, *(f'o-color-{i}' for i in range(1, 6))]
        names += [name for name in ('input', 'body') if is_set(name)]
        index = 1
        while f'o-cc{index}-bg' in root:
            names.append(f'o-cc{index}-bg')
            names += [
                name for key in ('text', 'link', 'btn-primary', 'btn-primary-border', 'btn-secondary', 'btn-secondary-border')
                if is_set(name := f'o-cc{index}-{key}')
            ]
            index += 1
        colors = {name: root[f'{name}-base' if name.endswith('-link') else name] for name in names}
        areas = {area: root.get(area, '') for area in cs.AREAS}
        self.authenticate('admin', 'admin')
        response = self.make_jsonrpc_request('/website/theme_computed_colors', {
            'colors': colors,
            'user_keys': sorted(user_keys),
            'min_contrast_ratio': float(root['o-min-contrast-ratio']),
            'areas': areas,
        })

        theme_gates = website.with_context(website_id=website.id)._get_theme_gates().split()
        for gate, is_on in response['gates'].items():
            self.assertEqual(is_on, gate in theme_gates, gate)
        self.assertGreater(len(response['values']), 300)
        for name, value in response['values'].items():
            with self.subTest(name=name):
                self.assertIn(name, root)
                compiled = root[name]
                if (color := cs.parse_color(value)) and (compiled_color := cs.parse_color(compiled)):
                    # Sass keeps HSL adjustments unrounded but prints them
                    # rounded: one unit apart at most.
                    for channel, compiled_channel in zip(color, compiled_color):
                        self.assertAlmostEqual(channel, compiled_channel, delta=1.01)
                elif name.endswith('-rgb'):
                    for channel, compiled_channel in zip(value.split(','), compiled.split(','), strict=True):
                        self.assertAlmostEqual(float(channel), float(compiled_channel), delta=1.01)
                else:
                    self.assertEqual(value, compiled)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteThemePreviewViews(odoo.tests.HttpCase):
    """
    Tests for `?theme_preview_views`: a page rendered as if some views were
    toggled, for the builder to preview them before they are saved.
    """

    def test_preview_views(self):
        header = '<header id="top"'
        hide_header = 'theme_preview_views={"website.option_layout_hide_header": true}'
        # Visitors: the parameter is ignored.
        self.assertIn(header, self.url_open(f'/?{hide_header}').text)
        # Internal users who aren't designers too.
        new_test_user(self.env, login='internal', groups='base.group_user')
        self.authenticate('internal', 'internal')
        self.assertIn(header, self.url_open(f'/?{hide_header}').text)
        self.authenticate('admin', 'admin')
        self.assertNotIn(header, self.url_open(f'/?{hide_header}').text)
        # Nothing written, and the preview isn't cached for the normal render.
        self.assertFalse(self.env['website'].with_context(website_id=1).is_view_active('website.option_layout_hide_header'))
        self.assertIn(header, self.url_open('/').text)
        for value in ('nonsense', '[]'):
            with self.subTest(value=value):
                response = self.url_open(f'/?theme_preview_views={value}')
                self.assertEqual(response.status_code, 200)
                self.assertIn(header, response.text)

    def test_preview_views_qweb_only(self):
        """ Only QWeb views are previewed: a backend view toggled through the
        context would be cached for everyone (its cache key ignores it). """
        self.env['ir.ui.view'].create({
            'name': 'Partner form marker',
            'key': 'website.test_partner_form_marker',
            'model': 'res.partner',
            'inherit_id': self.ref('base.view_partner_form'),
            'arch': '<field name="name" position="after"><field name="ref" class="o_test_marker"/></field>',
        })
        Partner = self.env['res.partner'].with_context(website_id=1)
        Partner.with_context(website_preview_views=(('website.test_partner_form_marker', False),)).get_views([(False, 'form')])
        arch = Partner.get_views([(False, 'form')])['views']['form']['arch']
        self.assertIn('o_test_marker', arch)

    def test_header_content_width_marked(self):
        """ Each header layout marks the elements printing its content width,
        where the builder previews it (not the mobile header's container). """
        self.authenticate('admin', 'admin')
        # The sidebar has no content width (a width of its own).
        for layout in ['default', 'hamburger', 'vertical', 'search', 'stretch', 'boxed',
                       'sales_one', 'sales_two', 'sales_three', 'sales_four']:
            with self.subTest(layout=layout):
                views = json.dumps({
                    'website.template_header_default': layout == 'default',
                    f'website.template_header_{layout}': True,
                    'website.header_width_full': True,
                })
                tree = html.fromstring(self.url_open(f'/?theme_preview_views={views}').content)
                marked = tree.xpath('//header[@id="top"]//*[contains(concat(" ", @class, " "), " o_header_content_width ")]')
                self.assertTrue(marked)
                for el in marked:
                    self.assertIn('container-fluid', el.get('class').split())
                mobile = tree.xpath('//header[@id="top"]//*[contains(@class, "o_header_mobile")]//*[contains(@class, "o_header_content_width")]')
                self.assertFalse(mobile)
