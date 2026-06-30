# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@tagged('-at_install', 'post_install')
class WebManifestRoutesTest(SelfOrderCommonTest):

    def test_webmanifest_scoped_icon_with_default(self):
        self.authenticate('admin', 'admin')
        manifest_url = f'/web/manifest.scoped_app_manifest?app_id=pos_self_order&path=/pos-self/{self.pos_config.id}'
        response = self.url_open(manifest_url)
        response.raise_for_status()
        data = response.json()
        self.assertEqual(data['name'], self.pos_config.name)
        self.assertCountEqual(data["icons"], [
            {'src': '/point_of_sale/static/description/icon.svg', 'sizes': 'any', 'type': 'image/svg+xml'}
        ])

    def test_webmanifest_scoped_icon_withoutdefault(self):
        self.env.company.uses_default_logo = False
        self.authenticate('admin', 'admin')
        manifest_url = f'/web/manifest.scoped_app_manifest?app_id=pos_self_order&path=/pos-self/{self.pos_config.id}'
        response = self.url_open(manifest_url)
        response.raise_for_status()
        data = response.json()
        self.assertEqual(data['name'], self.pos_config.name)
        icon_src = f'/web/image?model=res.company&id={self.env.company.id}&field=logo&height=192&width=192'
        self.assertCountEqual(data['icons'], [
            {'src': icon_src, 'sizes': 'any', 'type': 'image/png'}
        ])
