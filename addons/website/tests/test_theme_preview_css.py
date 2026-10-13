# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from odoo.tests.common import JsonRpcException, new_test_user
from odoo.tools import mute_logger

USER_VALUES_URL = '/website/static/src/scss/options/user_values.scss'
PALETTE_URL = '/website/static/src/scss/options/colors/user_color_palette.scss'


@odoo.tests.common.tagged('post_install', '-at_install')
class TestThemePreviewCss(odoo.tests.HttpCase):

    def setUp(self):
        super().setUp()
        self.website = self.env['website'].browse(self.ref('base.default_website'))
        self.Assets = self.env['website.assets'].with_context(website_id=self.website.id)

    def _get_preview_css(self, values_by_url):
        # A whole frontend compile: longer than the default timeout on slow machines.
        return self.make_jsonrpc_request('/website/theme_preview_css', {'values_by_url': values_by_url}, timeout=60)

    def _count_records(self):
        return [self.env[model].search_count([]) for model in ('ir.attachment', 'ir.asset')]

    def test_preview_css(self):
        self.Assets.make_scss_customization(USER_VALUES_URL, {'font-size-base': '1.0625rem'})
        records = self._count_records()
        saved_content = self.Assets._get_scss_content(USER_VALUES_URL)
        self.authenticate('admin', 'admin')

        css = self._get_preview_css({
            USER_VALUES_URL: {'font-size-base': '1.1875rem'},
            PALETTE_URL: {'o-color-1': '#0a1b2c'},
        })
        self.assertRegex(css, r'--font-size-base:\s*1\.1875rem')
        self.assertNotRegex(css, r'--font-size-base:\s*1\.0625rem')
        self.assertRegex(css, r'--o-color-1:\s*#0a1b2c')
        # Nothing written: the saved customization stays as it was.
        self.assertEqual(self._count_records(), records)
        self.assertEqual(self.Assets._get_scss_content(USER_VALUES_URL), saved_content)

    def test_preview_css_palette_switch(self):
        self.Assets.make_scss_customization(PALETTE_URL, {'o-color-1': '#0a1b2c', 'o-color-2': '#1b2c3d'})
        self.authenticate('admin', 'admin')

        # As saved: the palette switch resets the colors, then a color
        # changed after it is written.
        css = self._get_preview_css({
            USER_VALUES_URL: {'color-palettes-name': "'base-2'"},
            PALETTE_URL: {'o-color-2': '#2c3d4e'},
        })
        self.assertNotIn('#0a1b2c', css)
        self.assertRegex(css, r'--o-color-2:\s*#2c3d4e')
        self.assertIn('#0a1b2c', self.Assets._get_scss_content(PALETTE_URL))

    def test_preview_css_compile_error(self):
        self.authenticate('admin', 'admin')
        with mute_logger('odoo.addons.base.models.assetsbundle', 'odoo.http'):
            with self.assertRaisesRegex(JsonRpcException, 'UserError'):
                self._get_preview_css({USER_VALUES_URL: {'font-size-base': 'calc(1rem +'}})

    def test_preview_css_designers_only(self):
        new_test_user(self.env, login='restricted', groups='base.group_user,website.group_website_restricted_editor')
        self.authenticate('restricted', 'restricted')
        with mute_logger('odoo.http'):
            with self.assertRaisesRegex(JsonRpcException, 'Forbidden'):
                self._get_preview_css({USER_VALUES_URL: {'font-size-base': '1.1875rem'}})
