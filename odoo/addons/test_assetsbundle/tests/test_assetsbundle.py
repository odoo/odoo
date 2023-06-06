# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
from lxml import etree
import os
import time
from unittest import skip
from unittest.mock import Mock, patch
import textwrap
import pathlib
import lxml
import base64

import odoo
from odoo import api, http
from odoo.addons import __path__ as ADDONS_PATH
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.base.models.ir_asset import AssetPaths
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.modules.module import get_resource_path, get_manifest
from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase
from odoo.addons.base.models.ir_qweb import QWebException
from odoo.tools import mute_logger, func


GETMTINE = os.path.getmtime


class TestAddonPaths(TransactionCase):
    def test_operations(self):
        asset_paths = AssetPaths()
        self.assertFalse(asset_paths.list)

        asset_paths.append([
            ('/home/user/odoo/addons/web/a', '/web/a', 1),
            ('/home/user/odoo/addons/web/c', '/web/c', 1),
            ('/home/user/odoo/addons/web/d', '/web/d', 1),
        ], 'bundle1')
        self.assertEqual(asset_paths.list, [
            ('/home/user/odoo/addons/web/a', '/web/a', 'bundle1', 1),
            ('/home/user/odoo/addons/web/c', '/web/c', 'bundle1', 1),
            ('/home/user/odoo/addons/web/d', '/web/d', 'bundle1', 1),
        ])

        # append with a duplicate of 'c'
        asset_paths.append([
            ('/home/user/odoo/addons/web/c', '/web/c', 1),
            ('/home/user/odoo/addons/web/f', '/web/f', 1),
        ], 'bundle2')
        self.assertEqual(asset_paths.list, [
            ('/home/user/odoo/addons/web/a', '/web/a', 'bundle1', 1),
            ('/home/user/odoo/addons/web/c', '/web/c', 'bundle1', 1),
            ('/home/user/odoo/addons/web/d', '/web/d', 'bundle1', 1),
            ('/home/user/odoo/addons/web/f', '/web/f', 'bundle2', 1),
        ])

        # insert with a duplicate of 'c' after 'c'
        asset_paths.insert([
            ('/home/user/odoo/addons/web/c', '/web/c', 1),
            ('/home/user/odoo/addons/web/e', '/web/e', 1),
        ], 'bundle3', 3)
        self.assertEqual(asset_paths.list, [
            ('/home/user/odoo/addons/web/a', '/web/a', 'bundle1', 1),
            ('/home/user/odoo/addons/web/c', '/web/c', 'bundle1', 1),
            ('/home/user/odoo/addons/web/d', '/web/d', 'bundle1', 1),
            ('/home/user/odoo/addons/web/e', '/web/e', 'bundle3', 1),
            ('/home/user/odoo/addons/web/f', '/web/f', 'bundle2', 1),
        ])

        # insert with a duplicate of 'd' before 'd'
        asset_paths.insert([
            ('/home/user/odoo/addons/web/b', '/web/b', 1),
            ('/home/user/odoo/addons/web/d', '/web/d', 1)
        ], 'bundle4', 1)
        self.assertEqual(asset_paths.list, [

            ('/home/user/odoo/addons/web/a', '/web/a', 'bundle1', 1),
            ('/home/user/odoo/addons/web/b', '/web/b', 'bundle4', 1),
            ('/home/user/odoo/addons/web/c', '/web/c', 'bundle1', 1),
            ('/home/user/odoo/addons/web/d', '/web/d', 'bundle1', 1),
            ('/home/user/odoo/addons/web/e', '/web/e', 'bundle3', 1),
            ('/home/user/odoo/addons/web/f', '/web/f', 'bundle2', 1),
        ])

        # remove
        asset_paths.remove([
            ('/home/user/odoo/addons/web/c', '/web/c', 1),
            ('/home/user/odoo/addons/web/d', '/web/d', 1),
            ('/home/user/odoo/addons/web/g', '/web/g', 1)
        ], 'bundle5')
        self.assertEqual(asset_paths.list, [
            ('/home/user/odoo/addons/web/a', '/web/a', 'bundle1', 1),
            ('/home/user/odoo/addons/web/b', '/web/b', 'bundle4', 1),
            ('/home/user/odoo/addons/web/e', '/web/e', 'bundle3', 1),
            ('/home/user/odoo/addons/web/f', '/web/f', 'bundle2', 1),
        ])


class AddonManifestPatched(TransactionCase):
    def setUp(self):
        super().setUp()

        self.installed_modules = {'base', 'test_assetsbundle'}
        self.manifests = {
            'base': get_manifest('base'),
            'web': get_manifest('web'),
            'test_assetsbundle': get_manifest('test_assetsbundle'),
        }

        self.patch(self.env.registry, '_init_modules', self.installed_modules)
        self.patch(odoo.modules.module, 'get_manifest', Mock(side_effect=lambda module: self.manifests.get(module, {})))


class FileTouchable(AddonManifestPatched):
    def setUp(self):
        super(FileTouchable, self).setUp()
        self.touches = {}

    def _touch(self, filepath, touch_time=None):
        self.touches[filepath] = touch_time or time.time()
        return patch('os.path.getmtime', lambda filename: self.touches.get(filename) or GETMTINE(filename))

@tagged('-at_install', 'post_install')
class Test404(HttpCase):
    def get_assets_node_cache(self):
        return [e for e in self.env.registry._Registry__cache.d if e[0] == 'ir.qweb' and '_generate_' in str(e[1])]  #_generate_asset_nodes_cache

    def test_rollback(self):
        """
        In some rare case, attachments can be generatted, added to the cache but the transaction is rollbacked leading to 404
        this actually tests the add_post_rollback behaviour
        """
        self.env['ir.attachment'].search([('url', '=like', '/web/assets/%web.assets_frontend%')]).unlink()
        self.env.registry._clear_cache()
        self.url_open('/some_404_routes')
        self.assertFalse(self.get_assets_node_cache(), 'orm_cache should be emptied by rollback')
        self.assertFalse(self.env['ir.attachment'].search([('url', '=like', '/web/assets/%web.assets_frontend%%')]), "attachments should have been rollbacked")
        self.url_open('/')
        self.assertTrue(self.env['ir.attachment'].search([('url', '=like', '/web/assets/%web.assets_frontend%%')]), "attachments should have been generated as expected")
        self.assertTrue(self.get_assets_node_cache(), 'orm_cache should remain populated')
        self.env.registry._clear_cache()

class TestJavascriptAssetsBundle(FileTouchable):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # this is mainly to avoid tests breaking when executed after pre-generate
        cls.maxDiff = 10000
        cls.env['ir.attachment'].search([('url', '=like', '/web/assets/%test_assetsbundle%')]).unlink()

    def setUp(self):
        super(TestJavascriptAssetsBundle, self).setUp()
        self.jsbundle_name = 'test_assetsbundle.bundle1'
        self.cssbundle_name = 'test_assetsbundle.bundle2'

    def _get_asset(self, bundle, rtl=False, debug_assets=False):
        files, _ = self.env['ir.qweb']._get_asset_content(bundle)
        return AssetsBundle(bundle, files, env=self.env, debug_assets=debug_assets, rtl=rtl)

    def _any_ira_for_bundle(self, extension, rtl=False):
        """ Returns all ir.attachments associated to a bundle, regardless of the verion.
        """
        bundle = self.jsbundle_name if extension in ['js', 'min.js'] else self.cssbundle_name
        rtl = 'rtl/' if rtl and extension in ['css', 'min.css'] else ''
        url = f'/web/assets/%-%/{rtl}{bundle}.{extension}'
        domain = [('url', '=like', url)]
        return self.env['ir.attachment'].search(domain)

    def test_01_generation(self):
        """ Checks that a bundle creates an ir.attachment record when its `js` method is called
        for the first time and this ir.attachment is different depending on `is_minified` param.
        """
        self.bundle = self._get_asset(self.jsbundle_name)

        # there shouldn't be any minified attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 0,
                         "there shouldn't be any minified attachment associated to this bundle")
        self.assertEqual(len(self.bundle.get_attachments('min.js')), 0,
                         "there shouldn't be any minified attachment associated to this bundle")

        # trigger the first generation and, thus, the first save in database
        self.bundle.js()

        # there should be one minified attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified attachment associated to this bundle")
        self.assertEqual(len(self.bundle.get_attachments('min.js')), 1,
                         "there should be one minified attachment associated to this bundle")

        # there shouldn't be any non-minified attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('js')), 0,
                         "there shouldn't be any non-minified attachment associated to this bundle")
        self.assertEqual(len(self.bundle.get_attachments('js')), 0,
                         "there shouldn't be any non-minified attachment associated to this bundle")

        # trigger the first generation and, thus, the first save in database for the non-minified version.
        self.bundle.js(is_minified=False)

        # there should be one non-minified attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('js')), 1,
                         "there should be one non-minified attachment associated to this bundle")
        self.assertEqual(len(self.bundle.get_attachments('js')), 1,
                         "there should be one non-minified attachment associated to this bundle")

    def test_02_access(self):
        """ Checks that the bundle's cache is working, i.e. that the bundle creates only one
        ir.attachment record when rendered multiple times.
        """
        bundle0 = self._get_asset(self.jsbundle_name)
        bundle0.js()

        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified attachment associated to this bundle")

        version0 = bundle0.get_version('js')
        ira0 = self._any_ira_for_bundle('min.js')
        date0 = ira0.create_date

        bundle1 = self._get_asset(self.jsbundle_name)
        bundle1.js()

        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified attachment associated to this bundle")

        version1 = bundle1.get_version('js')
        ira1 = self._any_ira_for_bundle('min.js')
        date1 = ira1.create_date

        self.assertEqual(version0, version1,
                         "the version should not be changed because the bundle hasn't changed")
        self.assertEqual(date0, date1,
                         "the date of creation of the ir.attachment should not change because the bundle is unchanged")

    def test_03_date_invalidation(self):
        """ Checks that a bundle is invalidated when one of its assets' modification date is changed.
        """
        bundle0 = self._get_asset(self.jsbundle_name, debug_assets=True)
        bundle0.js()
        last_modified0 = bundle0.get_checksum('js')
        version0 = bundle0.get_version('js')

        path = get_resource_path('test_assetsbundle', 'static', 'src', 'js', 'test_jsfile1.js')
        bundle1 = self._get_asset(self.jsbundle_name, debug_assets=True)

        with self._touch(path):
            bundle1.js()
            last_modified1 = bundle1.get_checksum('js')
            version1 = bundle1.get_version('js')
            self.assertNotEqual(last_modified0, last_modified1,
                                "the creation date of the ir.attachment should change because the bundle has changed.")
            self.assertNotEqual(version0, version1,
                                "the version must should because the bundle has changed.")

            # check if the previous attachment is correctly cleaned
            self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                             "there should be one minified attachment associated to this bundle")

    def test_04_content_invalidation(self):
        """ Checks that a bundle is invalidated when its content is modified by adding a file to
        source.
        """
        bundle0 = self._get_asset(self.jsbundle_name)
        bundle0.js()
        files0 = bundle0.files
        version0 = bundle0.get_version('js')

        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified attachment associated to this bundle")

        self.env['ir.asset'].create({
            'name': 'test bundle inheritance',
            'bundle': self.jsbundle_name,
            'path': 'test_assetsbundle/static/src/js/test_jsfile4.js',
        })

        bundle1 = self._get_asset(self.jsbundle_name)
        bundle1.js()
        files1 = bundle1.files
        version1 = bundle1.get_version('js')

        self.assertNotEqual(files0, files1,
                            "the list of files should be different because a file has been added to the bundle")
        self.assertNotEqual(version0, version1,
                            "the version should be different because a file has been added to the bundle")

        # check if the previous attachment are correctly cleaned
        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified attachment associated to this bundle")

    def test_05_normal_mode(self):
        """ Checks that a bundle rendered in normal mode outputs minified assets
            and create a minified ir.attachment.
        """
        debug_bundle = self._get_asset(self.jsbundle_name)
        content = debug_bundle.get_links()
        # there should be a minified file
        self.assertIn('test_assetsbundle.bundle1.min.js', content[0][0])

        # there should be one minified assets created in normal mode
        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified assets created in normal mode")

        # there shouldn't be any non-minified assets created in normal mode
        self.assertEqual(len(self._any_ira_for_bundle('js')), 0,
                         "there shouldn't be any non-minified assets created in normal mode")

    def test_07_debug_assets(self):
        """ Checks that a bundle rendered in debug assets mode outputs non-minified assets
            and create an non-minified ir.attachment at the .
        """
        debug_bundle = self._get_asset(self.jsbundle_name, debug_assets=True)
        content = debug_bundle.get_links()
        # there should be a minified file
        self.assertIn('test_assetsbundle.bundle1.js', content[0][0], "there should be one non-minified assets created in debug assets mode")

        # there shouldn't be any minified assets created in debug mode
        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 0,
                         "there shouldn't be any minified assets created in debug assets mode")

        # there should be one non-minified assets created in debug mode
        self.assertEqual(len(self._any_ira_for_bundle('js')), 1,
                         "there should be one non-minified assets without a version in its url created in debug assets mode")

    def test_08_css_generation3(self):
        # self.cssbundle_xlmid contains 3 rules (not checked below)
        self.bundle = self._get_asset(self.cssbundle_name)
        self.bundle.css()
        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)
        self.assertEqual(len(self.bundle.get_attachments('min.css')), 1)

    def test_09_css_access(self):
        """ Checks that the bundle's cache is working, i.e. that a bundle creates only enough
        ir.attachment records when rendered multiple times.
        """
        bundle0 = self._get_asset(self.cssbundle_name)
        bundle0.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        version0 = bundle0.get_version('css')
        ira0 = self._any_ira_for_bundle('min.css')
        date0 = ira0.create_date

        bundle1 = self._get_asset(self.cssbundle_name)
        bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        version1 = bundle1.get_version('css')
        ira1 = self._any_ira_for_bundle('min.css')
        date1 = ira1.create_date

        self.assertEqual(version0, version1)
        self.assertEqual(date0, date1)

    def test_11_css_content_invalidation(self):
        """ Checks that a bundle is invalidated when its content is modified by adding a file to
        source.
        """
        bundle0 = self._get_asset(self.cssbundle_name)
        bundle0.css()
        files0 = bundle0.files
        version0 = bundle0.get_version('css')

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        self.env['ir.asset'].create({
            'name': 'test bundle inheritance',
            'bundle': self.cssbundle_name,
            'path': 'test_assetsbundle/static/src/css/test_cssfile2.css',
        })

        bundle1 = self._get_asset(self.cssbundle_name)
        bundle1.css()
        files1 = bundle1.files
        version1 = bundle1.get_version('css')

        self.assertNotEqual(files0, files1)
        self.assertNotEqual(version0, version1)

        # check if the previous attachment are correctly cleaned
        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

    def test_12_css_debug(self):
        """ Check that a bundle in debug mode outputs non-minified assets.
        """
        debug_bundle = self._get_asset(self.cssbundle_name, debug_assets=True)
        content = debug_bundle.get_links()
        # there should be a minified file
        self.assertEqual(content[0][0], '/web/assets/debug/test_assetsbundle.bundle2.css')

        # there should be one css asset created in debug mode
        self.assertEqual(len(self._any_ira_for_bundle('css')), 1,
                         'there should be one css asset created in debug mode')

    def test_14_duplicated_css_assets(self):
        """ Checks that if the bundle's ir.attachment record is duplicated, the bundle is only sourced once. This could
        happen if multiple transactions try to render the bundle simultaneously.
        """
        bundle0 = self._get_asset(self.cssbundle_name)
        bundle0.css()
        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        # duplicate the asset bundle
        ira0 = self._any_ira_for_bundle('min.css')
        ira1 = ira0.copy()
        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 2)
        self.assertEqual(ira0.store_fname, ira1.store_fname)

        # the ir.attachment records should be deduplicated in the bundle's content
        content = bundle0.get_links()
        self.assertIn('test_assetsbundle.bundle2.min.css', content[0][0])

    # Language direction specific tests

    def test_15_rtl_css_generation(self):
        """ Checks that a bundle creates an ir.attachment record when its `css` method is called
        for the first time for language with different direction and separate bundle is created for rtl direction.
        """
        self.bundle = self._get_asset(self.cssbundle_name, rtl=True)

        # there shouldn't be any attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('min.css', rtl=True)), 0)
        self.assertEqual(len(self.bundle.get_attachments('min.css')), 0)

        # trigger the first generation and, thus, the first save in database
        self.bundle.css()

        # there should be one attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('min.css', rtl=True)), 1)
        self.assertEqual(len(self.bundle.get_attachments('min.css')), 1)

    def test_16_ltr_and_rtl_css_access(self):
        """ Checks that the bundle's cache is working, i.e. that the bundle creates only one
        ir.attachment record when rendered multiple times for rtl direction also check we have two css bundles,
        one for ltr and one for rtl.
        """
        # Assets access for en_US language
        ltr_bundle0 = self._get_asset(self.cssbundle_name)
        ltr_bundle0.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        ltr_version0 = ltr_bundle0.get_version('css')
        ltr_ira0 = self._any_ira_for_bundle('min.css')
        ltr_date0 = ltr_ira0.create_date

        ltr_bundle1 = self._get_asset(self.cssbundle_name)
        ltr_bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        ltr_version1 = ltr_bundle1.get_version('css')
        ltr_ira1 = self._any_ira_for_bundle('min.css')
        ltr_date1 = ltr_ira1.create_date

        self.assertEqual(ltr_version0, ltr_version1)
        self.assertEqual(ltr_date0, ltr_date1)

        rtl_bundle0 = self._get_asset(self.cssbundle_name, rtl=True)
        rtl_bundle0.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css', rtl=True)), 1)

        rtl_version0 = rtl_bundle0.get_version('css')
        rtl_ira0 = self._any_ira_for_bundle('min.css', rtl=True)
        rtl_date0 = rtl_ira0.create_date

        rtl_bundle1 = self._get_asset(self.cssbundle_name, rtl=True)
        rtl_bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css', rtl=True)), 1)

        rtl_version1 = rtl_bundle1.get_version('css')
        rtl_ira1 = self._any_ira_for_bundle('min.css', rtl=True)
        rtl_date1 = rtl_ira1.create_date

        self.assertEqual(rtl_version0, rtl_version1)
        self.assertEqual(rtl_date0, rtl_date1)

        # Checks rtl and ltr bundles are different
        self.assertNotEqual(ltr_ira1.id, rtl_ira1.id)

        # Check two bundles are available, one for ltr and one for rtl
        css_bundles = self.env['ir.attachment'].search([
            ('url', '=like', '/web/assets/%-%/{0}%.{1}'.format(self.cssbundle_name, 'min.css'))
        ])
        self.assertEqual(len(css_bundles), 2)

    def test_17_css_bundle_date_invalidation(self):
        """ Checks that both css bundles are invalidated when one of its assets' modification date is changed
        """
        ltr_bundle0 = self._get_asset(self.cssbundle_name, debug_assets=True)
        ltr_bundle0.css()
        ltr_last_modified0 = ltr_bundle0.get_checksum('css')
        ltr_version0 = ltr_bundle0.get_version('css')

        rtl_bundle0 = self._get_asset(self.cssbundle_name, rtl=True, debug_assets=True)
        rtl_bundle0.css()
        rtl_last_modified0 = rtl_bundle0.get_checksum('css')
        rtl_version0 = rtl_bundle0.get_version('css')

        # Touch test_cssfile1.css
        # Note: No lang specific context given while calling _get_asset so it will load assets for en_US
        path = get_resource_path('test_assetsbundle', 'static', 'src', 'css', 'test_cssfile1.css')
        ltr_bundle1 = self._get_asset(self.cssbundle_name, debug_assets=True)

        with self._touch(path):
            ltr_bundle1.css()
            ltr_last_modified1 = ltr_bundle1.get_checksum('css')
            ltr_version1 = ltr_bundle1.get_version('css')
            ltr_ira1 = self._any_ira_for_bundle('min.css')
            self.assertNotEqual(ltr_last_modified0, ltr_last_modified1)
            self.assertNotEqual(ltr_version0, ltr_version1)

            rtl_bundle1 = self._get_asset(self.cssbundle_name, rtl=True, debug_assets=True)

            rtl_bundle1.css()
            rtl_last_modified1 = rtl_bundle1.get_checksum('css')
            rtl_version1 = rtl_bundle1.get_version('css')
            rtl_ira1 = self._any_ira_for_bundle('min.css', rtl=True)
            self.assertNotEqual(rtl_last_modified0, rtl_last_modified1)
            self.assertNotEqual(rtl_version0, rtl_version1)

            # Checks rtl and ltr bundles are different
            self.assertNotEqual(ltr_ira1.id, rtl_ira1.id)

            # check if the previous attachment is correctly cleaned
            css_bundles = self.env['ir.attachment'].search([
                ('url', '=like', '/web/assets/%-%/{0}%.{1}'.format(self.cssbundle_name, 'min.css'))
            ])
            self.assertEqual(len(css_bundles), 2)

    def test_18_css_bundle_content_invalidation(self):
        """ Checks that a bundle is invalidated when its content is modified by adding a file to
        source.
        """
        # Assets for en_US
        ltr_bundle0 = self._get_asset(self.cssbundle_name)
        ltr_bundle0.css()
        ltr_files0 = ltr_bundle0.files
        ltr_version0 = ltr_bundle0.get_version('css')

        rtl_bundle0 = self._get_asset(self.cssbundle_name, rtl=True)
        rtl_bundle0.css()
        rtl_files0 = rtl_bundle0.files
        rtl_version0 = rtl_bundle0.get_version('css')

        css_bundles = self.env['ir.attachment'].search([
            ('url', '=like', '/web/assets/%-%/{0}%.{1}'.format(self.cssbundle_name, 'min.css'))
        ])
        self.assertEqual(len(css_bundles), 2)

        self.env['ir.asset'].create({
            'name': 'test bundle inheritance',
            'bundle': self.cssbundle_name,
            'path': 'test_assetsbundle/static/src/css/test_cssfile3.css',
        })

        ltr_bundle1 = self._get_asset(self.cssbundle_name)
        ltr_bundle1.css()
        ltr_files1 = ltr_bundle1.files
        ltr_version1 = ltr_bundle1.get_version('css')
        ltr_ira1 = self._any_ira_for_bundle('min.css')

        self.assertNotEqual(ltr_files0, ltr_files1)
        self.assertNotEqual(ltr_version0, ltr_version1)

        rtl_bundle1 = self._get_asset(self.cssbundle_name, rtl=True)
        rtl_bundle1.css()
        rtl_files1 = rtl_bundle1.files
        rtl_version1 = rtl_bundle1.get_version('css')
        rtl_ira1 = self._any_ira_for_bundle('min.css', rtl=True)

        self.assertNotEqual(rtl_files0, rtl_files1)
        self.assertNotEqual(rtl_version0, rtl_version1)

        # Checks rtl and ltr bundles are different
        self.assertNotEqual(ltr_ira1.id, rtl_ira1.id)

        # check if the previous attachment are correctly cleaned
        css_bundles = self.env['ir.attachment'].search([
            ('url', '=like', '/web/assets/%-%/{0}%.{1}'.format(self.cssbundle_name, 'min.css'))
        ])
        self.assertEqual(len(css_bundles), 2)

    def test_19_css_in_debug_assets(self):
        """ Checks that a bundle rendered in debug mode(assets) with right to left language direction stores css files in assets bundle.
        """
        debug_bundle = self._get_asset(self.cssbundle_name, rtl=True, debug_assets=True)
        content = debug_bundle.get_links()

        # there should be an css assets bundle in /debug/rtl if user's lang direction is rtl and debug=assets
        self.assertEqual('/web/assets/debug/rtl/{0}.css'.format(self.cssbundle_name), content[0][0],
                      "there should be an css assets bundle in /debug/rtl if user's lang direction is rtl and debug=assets")

        # there should be an css assets bundle created in /rtl if user's lang direction is rtl and debug=assets
        css_bundle = self.env['ir.attachment'].search([
            ('url', '=like', '/web/assets/%-%/rtl/{0}.css'.format(self.cssbundle_name))
        ])
        self.assertEqual(len(css_bundle), 1,
                         "there should be an css assets bundle created in /rtl if user's lang direction is rtl and debug=assets")

    def test_20_external_lib_assets(self):
        html = self.env['ir.ui.view']._render_template('test_assetsbundle.template2')
        attachments = self.env['ir.attachment'].search([('url', '=like', '/web/assets/%-%/test_assetsbundle.bundle4.%')])
        self.assertEqual(len(attachments), 2)

        format_data = {
            "js": attachments[0].url,
            "css": attachments[1].url,
        }
        self.assertEqual(str(html.strip()), ("""<!DOCTYPE html>
<html>
    <head>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="%(css)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="%(js)s" onerror="__odooAssetError=1"></script>
    </head>
    <body>
    </body>
</html>""" % format_data))

    def test_21_external_lib_assets_debug_mode(self):
        html = self.env['ir.ui.view']._render_template('test_assetsbundle.template2', {"debug": "assets"})
        attachments = self.env['ir.attachment'].search([('url', '=like', '%/test_assetsbundle.bundle4.js')])
        self.assertEqual(len(attachments), 1)

        format_data = {
            "css": '/web/assets/debug/test_assetsbundle.bundle4.css',
            "js": '/web/assets/debug/test_assetsbundle.bundle4.js',
        }
        self.assertEqual(str(html.strip()), ("""<!DOCTYPE html>
<html>
    <head>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="%(css)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="%(js)s" onerror="__odooAssetError=1"></script>
    </head>
    <body>
    </body>
</html>""" % format_data))


@tagged('-at_install', 'post_install')
class TestAssetsBundleInBrowser(HttpCase):
    def test_01_js_interpretation(self):
        """ Checks that the javascript of a bundle is correctly interpreted.
        """
        self.browser_js(
            "/test_assetsbundle/js",
            "a + b + c === 6 ? console.log('test successful') : console.log('error')",
            login="admin"
        )

    @skip("Feature Regression")
    def test_02_js_interpretation_inline(self):
        """ Checks that the javascript of a bundle is correctly interpretet when mixed with inline.
        """
        view_arch = """
        <data>
            <xpath expr="." position="inside">
                <script type="text/javascript">
                    var d = 4;
                </script>
            </xpath>
        </data>
        """
        self.env['ir.ui.view'].create({
            'name': 'test bundle inheritance inline js',
            'type': 'qweb',
            'arch': view_arch,
            'inherit_id': self.browse_ref('test_assetsbundle.bundle1').id,
        })
        self.env.flush_all()

        self.browser_js(
            "/test_assetsbundle/js",
            "a + b + c + d === 10 ? console.log('test successful') : console.log('error')",
            login="admin",
        )

    # LPE Fixme
    # Review point @al: is this really what we want people to do ?
    def test_03_js_interpretation_recommended_new_method(self):
        """ Checks the feature of test_02 is still produceable, but in another way
        '/web/content/<int:id>/<string: filename.js>',
        """
        code = b'const d = 4;'
        attach = self.env['ir.attachment'].create({
            'name': 'CustomJscode.js',
            'mimetype': 'text/javascript',
            'datas': base64.b64encode(code),
        })
        # Use this route (filename is necessary)
        custom_url = '/web/content/%s/%s' % (attach.id, attach.name)
        attach.url = custom_url

        self.env['ir.asset'].create({
            'name': 'lol',
            'bundle': 'test_assetsbundle.bundle1',
            'path': custom_url,
        })
        self.browser_js(
            "/test_assetsbundle/js",
            "a + b + c + d === 10 ? console.log('test successful') : console.log('error')",
            login="admin",
        )


class TestAssetsBundleWithIRAMock(FileTouchable):
    def setUp(self):
        super(TestAssetsBundleWithIRAMock, self).setUp()
        self.stylebundle_name = 'test_assetsbundle.bundle3'
        self.counter = counter = Counter()

        # patch methods 'create' and 'unlink' of model 'ir.attachment'
        origin_create = IrAttachment.create
        origin_unlink = AssetsBundle._unlink_attachments

        @api.model_create_multi
        def create(self, vals_list):
            counter.update(['create'] * len(vals_list))
            return origin_create(self, vals_list)

        def unlink(self, attachments):
            counter.update(['unlink'])
            return origin_unlink(self, attachments)

        self.patch(IrAttachment, 'create', create)
        self.patch(AssetsBundle, '_unlink_attachments', unlink)

    def _get_asset(self):
        with patch.object(type(self.env['ir.asset']), '_get_installed_addons_list', Mock(return_value=self.installed_modules)):
            return self.env['ir.qweb']._get_asset_bundle(self.stylebundle_name, debug_assets=True)

    def _bundle(self, asset, should_create, should_unlink, reason=''):
        self.counter.clear()
        asset.get_links()
        if should_create:
            self.assertEqual(self.counter['create'], 2, f'An attachment should have been created {reason}')
        else:
            self.assertEqual(self.counter['create'], 0, f'No attachment should have been created {reason}')

        if should_unlink:
            self.assertEqual(self.counter['unlink'], 2, f'An attachment should have been unlink {reason}')
        else:
            self.assertEqual(self.counter['unlink'], 0, f'No attachment should have been unlink {reason}')

    def test_01_debug_mode_assets(self):
        """ Checks that the ir.attachments records created for compiled assets in debug mode
        are correctly invalidated.
        """
        # Compile for the first time
        self._bundle(self._get_asset(), True, False, '(First access)')

        # Compile a second time, without changes
        self._bundle(self._get_asset(), False, False, '(Second access, no change)')

        # Touch the file and compile a third time
        path = get_resource_path('test_assetsbundle', 'static', 'src', 'scss', 'test_file1.scss')
        t = time.time() + 5
        asset = self._get_asset()
        with self._touch(path, t):
            self._bundle(asset, True, True)

            # Because we are in the same transaction since the beginning of the test, the first asset
            # created and the second one have the same write_date, but the file's last modified date
            # has really been modified. If we do not update the write_date to a posterior date, we are
            # not able to reproduce the case where we compile this bundle again without changing
            # anything.
            self.env['ir.attachment'].flush_model(['checksum', 'write_date'])
            self.cr.execute("update ir_attachment set write_date=clock_timestamp() + interval '10 seconds' where id = (select max(id) from ir_attachment)")
            self.env['ir.attachment'].invalidate_model(['write_date'])

            # Compile a fourth time, without changes
            self._bundle(self._get_asset(), False, False)


@tagged('assets_manifest')
class TestAssetsManifest(AddonManifestPatched):

    def make_asset_view(self, asset_key, t_call_assets_attrs=None):
        default_attrs = {
            't-js': 'true',
            't-css': 'false',
        }
        if t_call_assets_attrs:
            default_attrs.update(t_call_assets_attrs)

        attrs = ' '.join(['%s="%s"' % (k, v) for k, v in default_attrs.items()])
        arch = '''
            <div>
                <t t-call-assets="%(asset_key)s" %(attrs)s />
            </div>
        ''' % {
            'asset_key': asset_key,
            'attrs': attrs
        }

        view = self.env['ir.ui.view'].create({
            'name': 'test asset',
            'arch': arch,
            'type': 'qweb',
        })
        return view

    def assertStringEqual(self, reference, tested):
        tested = textwrap.dedent(tested).strip()
        reference = reference.strip()
        self.assertEqual(tested, reference)

    def test_01_globmanifest(self):
        view = self.make_asset_view('test_assetsbundle.manifest1')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest1.min.js')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;
            '''
        )

    def test_02_globmanifest_no_duplicates(self):
        view = self.make_asset_view('test_assetsbundle.manifest2')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest2.min.js')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;
            '''
        )

    def test_03_globmanifest_file_before(self):
        view = self.make_asset_view('test_assetsbundle.manifest3')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest3.min.js')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;
            '''
        )

    def test_04_globmanifest_with_irasset(self):
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.manifest4',
            'path': 'test_assetsbundle/static/src/js/test_jsfile1.js',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4.min.js')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            '''
        )

    def test_05_only_irasset(self):
        view = self.make_asset_view('test_assetsbundle.irasset1')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.irasset1',
            'path': 'test_assetsbundle/static/src/js/test_jsfile1.js',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irasset1.min.js')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            '''
        )

    def test_06_replace(self):
        view = self.make_asset_view('test_assetsbundle.manifest1')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.manifest1',
            'directive': 'replace',
            'target': 'test_assetsbundle/static/src/js/test_jsfile1.js',
            'path': 'http://external.link/external.js',
        })
        rendered = self.env['ir.qweb']._render(view.id)
        html_tree = lxml.etree.fromstring(rendered)
        scripts = html_tree.findall('script')
        self.assertEqual(len(scripts), 2)
        self.assertEqual(scripts[0].get('src'), 'http://external.link/external.js')

        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest1')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;
            '''
        )

    def test_06_2_replace(self):
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.manifest4',
            'directive': 'replace',
            'path': 'test_assetsbundle/static/src/js/test_jsfile1.js',
            'target': 'test_assetsbundle/static/src/js/test_jsfile3.js',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            '''
        )

    def test_06_3_replace_globs(self):
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'prepend',
            'bundle': 'test_assetsbundle.manifest4',
            'path': 'test_assetsbundle/static/src/js/test_jsfile4.js',
        })
        # asset is now: js_file4 ; js_file3
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.manifest4',
            'directive': 'replace',
            'path': 'test_assetsbundle/static/src/js/test_jsfile[12].js',
            'target': 'test_assetsbundle/static/src/js/test_jsfile[45].js',
        })
        # asset is now: js_file1 ; js_file2 ; js_file3
        # because js_file is replaced by 1 and 2
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_07_remove(self):
        view = self.make_asset_view('test_assetsbundle.manifest5')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.manifest5',
            'directive': 'remove',
            'path': 'test_assetsbundle/static/src/js/test_jsfile2.js',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest5')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;
            '''
        )

    def test_08_remove_inexistent_file(self):
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.remove_error',
            'path': '/test_assetsbundle/static/src/js/test_jsfile1.js',
        })

        view = self.make_asset_view('test_assetsbundle.remove_error')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.remove_error',
            'directive': 'remove',
            'path': 'test_assetsbundle/static/src/js/test_doesntexist.js',
        })
        with self.assertRaises(Exception) as cm:
            self.env['ir.qweb']._render(view.id)
        self.assertTrue(
            "['test_assetsbundle/static/src/js/test_doesntexist.js'] not found" in str(cm.exception)
        )

    def test_09_remove_wholeglob(self):
        view = self.make_asset_view('test_assetsbundle.manifest2')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.manifest2',
            'directive': 'remove',
            'path': 'test_assetsbundle/static/src/*/**',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest2.js')], order='create_date DESC', limit=1)
        # indeed everything in the bundle matches the glob, so there is no attachment
        self.assertFalse(attach)

    def test_10_prepend(self):
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'prepend',
            'bundle': 'test_assetsbundle.manifest4',
            'path': 'test_assetsbundle/static/src/js/test_jsfile1.js',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_11_include(self):
        view = self.make_asset_view('test_assetsbundle.irasset_include1')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'include',
            'bundle': 'test_assetsbundle.irasset_include1',
            'path': 'test_assetsbundle.manifest6',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irasset_include1')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_12_include2(self):
        view = self.make_asset_view('test_assetsbundle.manifest6')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest6')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_13_include_circular(self):
        view = self.make_asset_view('test_assetsbundle.irasset_include1')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'include',
            'bundle': 'test_assetsbundle.irasset_include1',
            'path': 'test_assetsbundle.irasset_include2',
        })
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'include',
            'bundle': 'test_assetsbundle.irasset_include2',
            'path': 'test_assetsbundle.irasset_include1',
        })

        with self.assertRaises(QWebException) as cm:
            self.env['ir.qweb']._render(view.id)
        error = str(cm.exception.__cause__)
        self.assertTrue(error)
        self.assertFalse(isinstance(error, RecursionError))
        self.assertTrue(
            'Circular assets bundle declaration:' in error
        )

    def test_13_2_include_recursive_sibling(self):
        view = self.make_asset_view('test_assetsbundle.irasset_include1')
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'include',
            'bundle': 'test_assetsbundle.irasset_include1',
            'path': 'test_assetsbundle.irasset_include2',
        })
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'include',
            'bundle': 'test_assetsbundle.irasset_include2',
            'path': 'test_assetsbundle.irasset_include3',
        })
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'include',
            'bundle': 'test_assetsbundle.irasset_include2',
            'path': 'test_assetsbundle.irasset_include4',
        })
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'directive': 'include',
            'bundle': 'test_assetsbundle.irasset_include4',
            'path': 'test_assetsbundle.irasset_include3',
        })
        self.env['ir.asset'].create({
            'name': 'test_jsfile4',
            'bundle': 'test_assetsbundle.irasset_include3',
            'path': 'test_assetsbundle/static/src/js/test_jsfile1.js',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irasset_include1')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            '''
        )

    def test_14_other_module(self):
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_other.mockmanifest1': [
                    ('include', 'test_assetsbundle.manifest4'),
                ]
            }
        }
        view = self.make_asset_view('test_other.mockmanifest1')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_other.mockmanifest1')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_15_other_module_append(self):
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_assetsbundle.manifest4': [
                    'test_assetsbundle/static/src/js/test_jsfile1.js',
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            '''
        )

    def test_16_other_module_prepend(self):
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_assetsbundle.manifest4': [
                    ('prepend', 'test_assetsbundle/static/src/js/test_jsfile1.js'),
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_17_other_module_replace(self):
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_assetsbundle.manifest4': [
                    ('replace', 'test_assetsbundle/static/src/js/test_jsfile3.js', 'test_assetsbundle/static/src/js/test_jsfile1.js'),
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            '''
        )

    def test_17_other_module_remove(self):
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_assetsbundle.manifest4': [
                    ('remove', 'test_assetsbundle/static/src/js/test_jsfile3.js'),
                    ('append', 'test_assetsbundle/static/src/js/test_jsfile1.js'),
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            '''
        )

    def test_18_other_module_external(self):
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_assetsbundle.manifest4': [
                    'http://external.link/external.js',
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.manifest4')
        rendered = self.env['ir.qweb']._render(view.id)
        html_tree = lxml.etree.fromstring(rendered)
        scripts = html_tree.findall('script')
        self.assertEqual(len(scripts), 2)
        self.assertEqual(scripts[0].get('src'), 'http://external.link/external.js')
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    #
    # LPE Fixme: Warning, this matches a change in behavior
    # Before this, each node within an asset could have a "media" and/or a "direction"
    # attribute to tell the browser to take preferably the css resource
    # in the relevant viewport or text direction
    #
    # with the new ir_assert mechanism, these attributes are only evaluated at the t-call-asset
    # step, that is, a step earlier than before, implicating a more restrictive usage
    #
    def test_19_css_specific_attrs_in_tcallassets(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irasset2',
            'path': 'http://external.css/externalstyle.css',
        })
        self.env['ir.asset'].create({
            'name': '2',
            'bundle': 'test_assetsbundle.irasset2',
            'path': 'test_assetsbundle/static/src/css/test_cssfile1.css',
        })
        view = self.make_asset_view('test_assetsbundle.irasset2', {
            't-js': 'false',
            't-css': 'true',
            'media': 'print',
        })

        rendered = self.env['ir.qweb']._render(view.id)
        html_tree = lxml.etree.fromstring(rendered)
        stylesheets = html_tree.findall('link')
        self.assertEqual(len(stylesheets), 2)
        self.assertEqual(stylesheets[0].get('href'), 'http://external.css/externalstyle.css')
        self.assertEqual(stylesheets[0].get('media'), 'print')

        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irasset2')], order='create_date DESC', limit=1)
        self.assertEqual(len(attach), 1)

    def test_20_css_base(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irasset2',
            'path': 'http://external.css/externalstyle.css',
        })
        self.env['ir.asset'].create({
            'name': '2',
            'bundle': 'test_assetsbundle.irasset2',
            'path': 'test_assetsbundle/static/src/scss/test_file1.scss',
        })
        view = self.make_asset_view('test_assetsbundle.irasset2', {
            't-js': 'false',
            't-css': 'true',
        })

        rendered = self.env['ir.qweb']._render(view.id)
        html_tree = lxml.etree.fromstring(rendered)
        stylesheets = html_tree.findall('link')
        self.assertEqual(len(stylesheets), 2)
        self.assertEqual(stylesheets[0].get('href'), 'http://external.css/externalstyle.css')
        for css in stylesheets:
            self.assertFalse(css.get('media'))

        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irasset2')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/scss/test_file1.scss */
             .rule1{color: black;}
            '''
        )

    def test_21_js_before_css(self):
        '''Non existing target node: ignore the manifest line'''
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_other.bundle4': [
                    ('before', 'test_assetsbundle/static/src/css/test_cssfile1.css', '/test_assetsbundle/static/src/js/test_jsfile4.js')
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.bundle4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.bundle4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_22_js_before_js(self):
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_assetsbundle.bundle4': [
                    ('before', '/test_assetsbundle/static/src/js/test_jsfile3.js', '/test_assetsbundle/static/src/js/test_jsfile4.js')
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.bundle4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.bundle4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_23_js_after_css(self):
        '''Non existing target node: ignore the manifest line'''
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_other.bundle4': [
                    ('after', 'test_assetsbundle/static/src/css/test_cssfile1.css', '/test_assetsbundle/static/src/js/test_jsfile4.js')
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.bundle4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.bundle4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_24_js_after_js(self):
        self.installed_modules.add('test_other')
        self.manifests['test_other'] = {
            'name': 'test_other',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
            'assets': {
                'test_assetsbundle.bundle4': [
                    ('after', '/test_assetsbundle/static/src/js/test_jsfile2.js', '/test_assetsbundle/static/src/js/test_jsfile4.js')
                ]
            }
        }
        view = self.make_asset_view('test_assetsbundle.bundle4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.bundle4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_25_js_before_js_in_irasset(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.bundle4',
            'path': '/test_assetsbundle/static/src/js/test_jsfile4.js',
            'target': '/test_assetsbundle/static/src/js/test_jsfile3.js',
            'directive': 'before',
        })
        view = self.make_asset_view('test_assetsbundle.bundle4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.bundle4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_26_js_after_js_in_irasset(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.bundle4',
            'path': '/test_assetsbundle/static/src/js/test_jsfile4.js',
            'target': '/test_assetsbundle/static/src/js/test_jsfile2.js',
            'directive': 'after',
        })
        view = self.make_asset_view('test_assetsbundle.bundle4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.bundle4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    def test_27_mixing_after_before_js_css_in_irasset(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.bundle4',
            'path': '/test_assetsbundle/static/src/js/test_jsfile4.js',
            'target': '/test_assetsbundle/static/src/css/test_cssfile1.css',
            'directive': 'after',
        })
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.bundle4',
            'path': '/test_assetsbundle/static/src/css/test_cssfile3.css',
            'target': '/test_assetsbundle/static/src/js/test_jsfile2.js',
            'directive': 'before',
        })
        view = self.make_asset_view('test_assetsbundle.bundle4', {
            't-js': 'true',
            't-css': 'true',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.bundle4')], order='create_date DESC', limit=2)
        attach_css = None
        attach_js = None
        for a in attach:
            if '.css' in a.url:
                attach_css = a
            elif '.js' in a.url:
                attach_js = a

        js_content = attach_js.raw.decode()
        self.assertStringEqual(
            js_content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

        css_content = attach_css.raw.decode()
        self.assertStringEqual(
            css_content,
            '''
            /* /test_assetsbundle/static/src/css/test_cssfile3.css */
            .rule4{color: green;}

            /* /test_assetsbundle/static/src/css/test_cssfile1.css */
            .rule1{color: black;}.rule2{color: yellow;}.rule3{color: red;}

            /* /test_assetsbundle/static/src/css/test_cssfile2.css */
            .rule4{color: blue;}
            '''
        )

    def test_28_js_after_js_in_irasset_wrong_path(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.wrong_path',
            'path': '/test_assetsbundle/static/src/js/test_jsfile4.js',
        })
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.wrong_path',
            'path': '/test_assetsbundle/static/src/js/test_jsfile1.js',
            'target': '/test_assetsbundle/static/src/js/doesnt_exist.js',
            'directive': 'after',
        })
        view = self.make_asset_view('test_assetsbundle.wrong_path')
        with self.assertRaises(Exception) as cm:
            self.env['ir.qweb']._render(view.id)
        self.assertTrue(
            "test_assetsbundle/static/src/js/doesnt_exist.js not found" in str(cm.exception)
        )

    def test_29_js_after_js_in_irasset_glob(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.manifest4',
            'path': '/test_assetsbundle/static/src/*/**',
            'target': '/test_assetsbundle/static/src/js/test_jsfile3.js',
            'directive': 'after',
        })
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;
            '''
        )

    def test_30_js_before_js_in_irasset_glob(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.manifest4',
            'path': '/test_assetsbundle/static/src/js/test_jsfile[124].js',
            'target': '/test_assetsbundle/static/src/js/test_jsfile3.js',
            'directive': 'before',
        })
        view = self.make_asset_view('test_assetsbundle.manifest4')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.manifest4')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            '''
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            '''
        )

    @mute_logger('odoo.addons.base.models.ir_asset')
    def test_31(self):
        path_to_dummy = '../../tests/dummy.js'
        me = pathlib.Path(__file__).parent.absolute()
        file_path = me.joinpath("..", path_to_dummy)  # assuming me = test_assetsbundle/tests
        self.assertTrue(os.path.isfile(file_path))

        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/test_assetsbundle/%s' % path_to_dummy,
        })
        view = self.make_asset_view('test_assetsbundle.irassetsec')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irassetsec')], order='create_date DESC', limit=1)
        self.assertIn(b"Could not get content for /test_assetsbundle/../../tests/dummy.js", attach.exists().raw)

    @mute_logger('odoo.addons.base.models.ir_asset')
    def test_32_a_relative_path_in_addon(self):
        path_to_dummy = '../../tests/dummy.xml'
        me = pathlib.Path(__file__).parent.absolute()
        file_path = me.joinpath("..", path_to_dummy)  # assuming me = test_assetsbundle/tests
        self.assertTrue(os.path.isfile(file_path))

        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/test_assetsbundle/%s' % path_to_dummy,
        })

        files = self.env['ir.asset']._get_asset_paths('test_assetsbundle.irassetsec', {})
        self.assertEqual(files, [('/test_assetsbundle/../../tests/dummy.xml', None, 'test_assetsbundle.irassetsec', None)])
        # TODO, validate this behaviour
        # the idea is that if the second element is False (not None) it will be added to the assetbundle, but considered in any case as an attachment url)

    @mute_logger('odoo.addons.base.models.ir_asset')
    def test_32_b_relative_path_outsied_addon(self):
        path_to_dummy = '../../tests/dummy.xml'
        me = pathlib.Path(__file__).parent.absolute()
        file_path = me.joinpath("..", path_to_dummy)  # assuming me = test_assetsbundle/tests
        self.assertTrue(os.path.isfile(file_path))

        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '%s' % path_to_dummy,
        })
        files = self.env['ir.asset']._get_asset_paths('test_assetsbundle.irassetsec', {})
        self.assertEqual(files, [('../../tests/dummy.xml', None, 'test_assetsbundle.irassetsec', None)])

    def test_33(self):
        self.manifests['notinstalled_module'] = {
            'name': 'notinstalled_module',
            'depends': ['test_assetsbundle'],
            'addons_path': pathlib.Path(__file__).resolve().parent,
        }
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/notinstalled_module/somejsfile.js',
        })
        view = self.make_asset_view('test_assetsbundle.irassetsec')
        with self.assertRaises(QWebException) as cm:
            self.env['ir.qweb']._render(view.id)

        self.assertTrue('Unallowed to fetch files from addon notinstalled_module' in str(cm.exception))

    def test_33bis_notinstalled_not_in_manifests(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/notinstalled_module/somejsfile.js',
        })
        self.make_asset_view('test_assetsbundle.irassetsec')
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irassetsec')], order='create_date DESC', limit=1)
        self.assertFalse(attach.exists())

    @mute_logger('odoo.addons.base.models.ir_asset')
    def test_34(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/test_assetsbundle/__manifest__.py',
        })
        view = self.make_asset_view('test_assetsbundle.irassetsec')
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irassetsec')], order='create_date DESC', limit=1)
        self.assertFalse(attach.exists())

    @mute_logger('odoo.addons.base.models.ir_asset')
    def test_35(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/test_assetsbundle/data/ir_asset.xml',
        })
        files = self.env['ir.asset']._get_asset_paths('test_assetsbundle.irassetsec', {})
        self.assertEqual(files, [('/test_assetsbundle/data/ir_asset.xml', None, 'test_assetsbundle.irassetsec', None)])

    def test_36(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/test_assetsbundle/static/accessible.xml',
        })
        files = self.env['ir.asset']._get_asset_paths('test_assetsbundle.irassetsec', {})
        modified = files[0][3]

        base_path = __file__.replace('/tests/test_assetsbundle.py', '')

        self.assertEqual(files, [(
            '/test_assetsbundle/static/accessible.xml',
            f'{base_path}/static/accessible.xml',
            'test_assetsbundle.irassetsec',
            modified
        )])

    def test_37_path_can_be_an_attachment(self):
        scss_code = base64.b64encode(b"""
            .my_div {
                &.subdiv {
                    color: blue;
                }
            }
        """)
        self.env['ir.attachment'].create({
            'name': 'my custom scss',
            'mimetype': 'text/scss',
            'type': 'binary',
            'url': 'test_assetsbundle/my_style_attach.scss',
            'datas': scss_code
        })

        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irasset_custom_attach',
            'path': 'test_assetsbundle/my_style_attach.scss',
        })
        view = self.make_asset_view('test_assetsbundle.irasset_custom_attach', {'t-css': True})
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irasset_custom_attach')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        # The scss should be compiled
        self.assertStringEqual(
            content,
            """
            /* test_assetsbundle/my_style_attach.scss */
             .my_div.subdiv{color: blue;}
            """
        )

@tagged('-at_install', 'post_install')
class AssetsNodeOrmCacheUsage(TransactionCase):

    def cache_keys(self):
        keys = self.env.registry._Registry__cache.d
        asset_keys = [key for key in keys if key[0] == 'ir.asset' and '_get_asset_paths' in str(key[1])] # ignore topological sort entry
        qweb_keys = [key for key in keys if key[0] == 'ir.qweb']
        return asset_keys, qweb_keys

    def test_assets_node_orm_cache_usage_debug(self):
        self.env.registry._clear_cache()

        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 0)
        self.assertEqual(len(qweb_keys), 0)

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', debug='tests')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', debug='1')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

        # in debug=assets, the ormcache is not used for _generate_asset_links_cache
        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', debug='assets')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

    def test_assets_node_orm_cache_usage_file_type(self):
        self.env.registry._clear_cache()

        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 0)
        self.assertEqual(len(qweb_keys), 0)

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', js=True, css=False)
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', js=False, css=True)
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 2)

        # NOTE: this result is not really desired but this is the current behaviour. In practice, we usually only generate one of them.
        # This could be enforced or avoided
        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', js=True, css=True)
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 3)


    def test_assets_node_orm_cache_usage_lang(self):
        self.env.registry._clear_cache()
        self.env['res.lang']._activate_lang('ar_SY')
        self.env['res.lang']._activate_lang('fr_FR')
        self.env['res.lang']._activate_lang('en_US')

        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 0)
        self.assertEqual(len(qweb_keys), 0)

        self.env['ir.qweb'].with_context(lang='fr_FR')._get_asset_nodes('web.assets_backend')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

        self.env['ir.qweb'].with_context(lang='en_US')._get_asset_nodes('web.assets_backend')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

        self.env['ir.qweb'].with_context(lang='ar_SY')._get_asset_nodes('web.assets_backend')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 2)  # a second cache entry is created for rtl

    def test_assets_node_orm_cache_usage_website(self):
        if self.env['ir.module.module'].search([('name', '=', 'website'), ('state', '=', 'uninstalled')]):
            return  # only makes sence if website is installed
        self.env.registry._clear_cache()

        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 0)
        self.assertEqual(len(qweb_keys), 0)

        self.env['ir.qweb'].with_context(website_id=None)._get_asset_nodes('web.assets_backend')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

        self.env['ir.qweb'].with_context(website_id=1)._get_asset_nodes('web.assets_backend')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 2)  # the content may be different for different websites, even if it is not always the case
        self.assertEqual(len(qweb_keys), 2)

    def test_assets_node_orm_cache_usage_node_flags(self):
        self.env.registry._clear_cache()

        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 0)
        self.assertEqual(len(qweb_keys), 0)

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1)
        self.assertEqual(len(qweb_keys), 1)

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', media='print')
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1, "media shouldn't create another entry")
        self.assertEqual(len(qweb_keys), 1, "media shouldn't create another entry")

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', defer_load=True)
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1, "defer_load shouldn't create another entry")
        self.assertEqual(len(qweb_keys), 1, "defer_load shouldn't create another entry")

        self.env['ir.qweb']._get_asset_nodes('web.assets_backend', lazy_load=True)
        asset_keys, qweb_keys = self.cache_keys()
        self.assertEqual(len(asset_keys), 1, "lazy_load shouldn't create another entry")
        self.assertEqual(len(qweb_keys), 1, "lazy_load shouldn't create another entry")
