# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import convert_file
from odoo.tools.misc import file_path


@tagged('-at_install', 'post_install')
class TestAsset(TransactionCase):

    def test_asset_tag(self):
        """
        Verify that assets defined with the <asset> tag are properly imported.
        """
        # Load new records
        convert_file(
            self.env, 'base',
            file_path('base/tests/asset_tag.xml'),
            {}, 'init', False, 'test'
        )
        active_keep_asset = self.env.ref('base.test_asset_tag_aaa')
        inactive_keep_asset = self.env.ref('base.test_asset_tag_iii')
        active_switch_asset_reset = self.env.ref('base.test_asset_tag_aia')
        active_switch_asset_ignore = self.env.ref('base.test_asset_tag_aii')
        inactive_switch_asset = self.env.ref('base.test_asset_tag_iaa')
        prepend_asset = self.env.ref('base.test_asset_tag_prepend')
        asset_with_extra_field = self.env.ref('base.test_asset_tag_extra')

        # Verify initial load
        self.assertEqual(prepend_asset._name, 'ir.asset', 'Model should be ir.asset')
        self.assertEqual(prepend_asset.name, 'Test asset tag with directive', 'Name not loaded')
        self.assertEqual(prepend_asset.directive, 'prepend', 'Directive not loaded')
        self.assertEqual(prepend_asset.bundle, 'test_asset_bundle', 'Bundle not loaded')
        self.assertEqual(prepend_asset.path, 'base/tests/something.scss', 'Path not loaded')
        self.assertEqual(asset_with_extra_field.sequence, 17, 'Sequence not loaded')
        self.assertTrue(active_keep_asset.active, 'Should be active')
        self.assertTrue(active_switch_asset_reset.active, 'Should be active')
        self.assertTrue(active_switch_asset_ignore.active, 'Should be active')
        self.assertFalse(inactive_keep_asset.active, 'Should be inactive')
        self.assertFalse(inactive_switch_asset.active, 'Should be inactive')

        # Patch records
        prepend_asset.name = 'changed'
        prepend_asset.directive = 'append'
        prepend_asset.bundle = 'changed'
        prepend_asset.path = 'base/tests/changed.scss'
        asset_with_extra_field.sequence = 3
        active_switch_asset_reset.active = False
        active_switch_asset_ignore.active = False
        inactive_switch_asset.active = True

        # Update records
        convert_file(
            self.env, 'base',
            file_path('base/tests/asset_tag.xml'),
            {
                'base.test_asset_tag_aaa': active_keep_asset.id,
                'base.test_asset_tag_iii': inactive_keep_asset.id,
                'base.test_asset_tag_aia': active_switch_asset_reset.id,
                'base.test_asset_tag_aii': active_switch_asset_ignore.id,
                'base.test_asset_tag_iaa': inactive_switch_asset.id,
                'base.test_asset_tag_prepend': prepend_asset.id,
                'base.test_asset_tag_extra': asset_with_extra_field.id,
            }, 'update', False, 'test'
        )

        # Verify updated load
        self.assertEqual(prepend_asset.name, 'Test asset tag with directive', 'Name not restored')
        self.assertEqual(prepend_asset.directive, 'prepend', 'Directive not restored')
        self.assertEqual(prepend_asset.bundle, 'test_asset_bundle', 'Bundle not restored')
        self.assertEqual(prepend_asset.path, 'base/tests/something.scss', 'Path not restored')
        self.assertEqual(asset_with_extra_field.sequence, 17, 'Sequence not restored')
        self.assertTrue(active_keep_asset.active, 'Should be active')
        self.assertTrue(active_switch_asset_reset.active, 'Should be reset to active')
        self.assertFalse(active_switch_asset_ignore.active, 'Should be kept inactive')
        self.assertFalse(inactive_keep_asset.active, 'Should be inactive')
        self.assertTrue(inactive_switch_asset.active, 'Should be kept active')
