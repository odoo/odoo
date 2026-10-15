# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.html_editor.tests.test_assets import LazyFrontendBundleCase


@tagged('post_install', '-at_install')
class TestAssets(LazyFrontendBundleCase):

    def test_assets_html_editor_not_in_frontend(self):
        self.assertNotInFrontend('website_profile.assets_html_editor')
