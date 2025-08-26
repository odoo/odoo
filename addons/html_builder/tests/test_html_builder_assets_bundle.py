
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tests.common import HttpCase


@odoo.tests.tagged('-at_install', 'post_install')
class TestHtmlBuilderAssetsBundle(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bundle = cls.env["ir.qweb"]._get_asset_bundle("html_builder.assets", True)

    def test_html_builder_assets_bundle_no_edit_scss(self):
        for file in self.bundle.files:
            filename = file["filename"]
            self.assertFalse(filename.endswith("edit.scss"), msg="html_builder.assets must not contain *.edit.scss files. Remove " + filename)
