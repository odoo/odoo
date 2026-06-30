# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestIrAsset(odoo.tests.HttpCase):

    def test_01_website_specific_assets(self):
        IrAsset = self.env['ir.asset']
        Website = self.env['website']

        website_1 = Website.create({'name': "Website 1"})
        website_2 = Website.create({'name': "Website 2"})

        assets = IrAsset.create([{
            'key': 'test0',
            'name': '0',
            'bundle': 'test_bundle.irasset',
            'path': '/website/test/base0.css',
        }, {
            'key': 'test1',
            'name': '1',
            'bundle': 'test_bundle.irasset',
            'path': '/website/test/base1.css',
        }, {
            'key': 'test2',
            'name': '2',
            'bundle': 'test_bundle.irasset',
            'path': '/website/test/base2.css',
        }])

        # For website 1, modify asset 1 and disable asset 2.
        assets[1].with_context(website_id=website_1.id).write({
            'path': '/website/test/specific1.css',
        })
        assets[2].with_context(website_id=website_1.id).write({
            'active': False,
        })

        files = IrAsset._get_asset_paths('test_bundle.irasset', {'website_id': website_1.id})
        self.assertEqual(len(files), 2, "There should be two assets in the specific website.")
        self.assertEqual(files[0][0], '/website/test/base0.css', "First asset should be the same as the base one.")
        self.assertEqual(files[1][0], '/website/test/specific1.css', "Second asset should be the specific one.")

        files = IrAsset._get_asset_paths('test_bundle.irasset', {'website_id': website_2.id})
        self.assertEqual(len(files), 3, "All three assets should be in the unmodified website.")
        self.assertEqual(files[0][0], '/website/test/base0.css', "First asset should be the base one.")
        self.assertEqual(files[1][0], '/website/test/base1.css', "Second asset should be the base one.")
        self.assertEqual(files[2][0], '/website/test/base2.css', "Third asset should be the base one.")
