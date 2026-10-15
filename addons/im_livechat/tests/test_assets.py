# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.html_editor.tests.test_assets import LazyFrontendBundleCase


@tagged('post_install', '-at_install')
class TestAssets(LazyFrontendBundleCase):

    def test_assets_embed_frontend_not_in_frontend(self):
        self.assertNotInFrontend('im_livechat.assets_embed_frontend', allowed={
            # icon mixins, needed by the livechat scss
            '/web/static/src/webclient/icons.scss',
            '/web/static/src/webclient/icons_mappings/rtl_icons.scss',
        })
