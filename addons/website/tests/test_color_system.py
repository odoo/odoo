# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import unittest

from PIL import ImageColor

from odoo.tests import BaseCase, tagged
from odoo.tools.misc import file_open, file_path

from odoo.addons.website import color_system as cs

try:
    import sass as libsass
except ImportError:
    libsass = None


@tagged('post_install', '-at_install')
@unittest.skipUnless(libsass, "libsass is not installed")
class TestColorSystem(BaseCase):
    """`color_system` computes the colors the compile does, for the preview of
    colors: compared with the SCSS functions and mixins it mirrors."""

    def compile(self, rules):
        """Values printed as custom properties by the given rules, compiled
        with the color functions of Bootstrap, web and html_editor."""
        imports = ''.join(f'@import "{file_path(path)}";\n' for path in (
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/src/scss/primary_variables.scss',
            'html_editor/static/src/scss/html_editor.variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/src/scss/bs_mixins_overrides.scss',
            'web/static/src/scss/utils.scss',
        ))
        source = f"""
            $white: #FFFFFF; $black: #000000;
            {imports}
            $color-contrast-light: #FFFFFF; $color-contrast-dark: #212529;
            $min-contrast-ratio: 2.9; $body-bg: #F6F5F4;
            a {{ {rules} }}
        """
        css = libsass.compile(string=source.replace('\\', '/'), precision=8, output_style='expanded')
        return dict(re.findall(r'--([\w-]+):\s*([^;]*);', css))

    def assertSameColor(self, scss_value, python_value, message):
        if isinstance(python_value, tuple):
            python_value = cs.format_color(python_value)
            # libsass prints some colors by their name.
            if re.fullmatch(r'[a-z]+', scss_value):
                scss_value = '#%02x%02x%02x' % ImageColor.getrgb(scss_value)
            scss_value = cs.format_color(cs.parse_color(scss_value))
        self.assertEqual(scss_value, python_value, message)

    def test_matches_scss(self):
        with file_open('website/static/src/scss/primary_variables.scss') as f:
            colors = sorted({color.upper() for color in re.findall(r'#[0-9a-fA-F]{6}\b', f.read())})
        self.assertGreater(len(colors), 50)
        contrast = cs.ColorContrast(cs.WHITE, cs.parse_color('#212529'), cs.parse_color('#F6F5F4'), 2.9)
        background = cs.parse_color('#1B1319')
        rules = []
        expected = {}
        for i, hex_color in enumerate(colors):
            color = cs.parse_color(hex_color)
            rules.append(f"""
                --contrast-{i}: #{{color-contrast({hex_color})}};
                --translucent-contrast-{i}: #{{color-contrast(rgba({hex_color}, 0.4))}};
                --link-{i}: #{{increase-contrast({hex_color}, #1B1319)}};
                --link-hover-{i}: #{{increase-contrast(darken({hex_color}, 15%), #1B1319)}};
                --lighten-{i}: #{{lighten({hex_color}, 40%)}};
                --lightness-{i}: #{{lightness({hex_color})}};
                @include o-print-button-variant('button-{i}', {hex_color}, #714B67);
                @include o-print-button-outline-variant('outline-{i}', {hex_color});
            """)
            expected.update({
                f'contrast-{i}': contrast(color),
                f'translucent-contrast-{i}': contrast(cs.with_alpha(color, 0.4)),
                f'link-{i}': cs.increase_contrast(color, background),
                f'link-hover-{i}': cs.increase_contrast(cs.adjust_lightness(color, -15), background),
                f'lighten-{i}': cs.adjust_lightness(color, 40),
                f'lightness-{i}': f'{cs.format_number(cs.lightness(color))}%',
                f'outline-{i}-contrast': contrast.button_outline_variant(color)['hover-color'],
                f'outline-{i}-rgb': cs.to_rgb(color),
            })
            variant = contrast.button_variant(color, cs.parse_color('#714B67'))
            variant['text'] = variant.pop('color')
            del variant['disabled-color']
            variant['focus-shadow-rgb'] = cs.to_rgb(variant['focus-shadow-rgb'])
            expected.update({f'button-{i}-{key}': value for key, value in variant.items()})
        compiled = self.compile(''.join(rules))
        for name, value in expected.items():
            self.assertSameColor(compiled[name], value, name)
