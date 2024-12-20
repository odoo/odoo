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

        asset_paths.append(['a', 'c', 'd'], 'module1', 'bundle1')
        self.assertEqual(asset_paths.list, [
            ('a', 'module1', 'bundle1'),
            ('c', 'module1', 'bundle1'),
            ('d', 'module1', 'bundle1'),
        ])

        # append with a duplicate of 'c'
        asset_paths.append(['c', 'f'], 'module2', 'bundle2')
        self.assertEqual(asset_paths.list, [
            ('a', 'module1', 'bundle1'),
            ('c', 'module1', 'bundle1'),
            ('d', 'module1', 'bundle1'),
            ('f', 'module2', 'bundle2'),
        ])

        # insert with a duplicate of 'c' after 'c'
        asset_paths.insert(['c', 'e'], 'module3', 'bundle3', 3)
        self.assertEqual(asset_paths.list, [
            ('a', 'module1', 'bundle1'),
            ('c', 'module1', 'bundle1'),
            ('d', 'module1', 'bundle1'),
            ('e', 'module3', 'bundle3'),
            ('f', 'module2', 'bundle2'),
        ])

        # insert with a duplicate of 'd' before 'd'
        asset_paths.insert(['b', 'd'], 'module4', 'bundle4', 1)
        self.assertEqual(asset_paths.list, [
            ('a', 'module1', 'bundle1'),
            ('b', 'module4', 'bundle4'),
            ('c', 'module1', 'bundle1'),
            ('d', 'module1', 'bundle1'),
            ('e', 'module3', 'bundle3'),
            ('f', 'module2', 'bundle2'),
        ])

        # remove
        asset_paths.remove(['c', 'd', 'g'], 'module5', 'bundle5')
        self.assertEqual(asset_paths.list, [
            ('a', 'module1', 'bundle1'),
            ('b', 'module4', 'bundle4'),
            ('e', 'module3', 'bundle3'),
            ('f', 'module2', 'bundle2'),
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
        self.patch(odoo.modules.module, '_get_manifest_cached', Mock(side_effect=lambda module: self.manifests.get(module, {})))


class FileTouchable(AddonManifestPatched):
    def setUp(self):
        super(FileTouchable, self).setUp()
        self.touches = {}

    def _touch(self, filepath, touch_time=None):
        self.touches[filepath] = touch_time or time.time()
        return patch('os.path.getmtime', lambda filename: self.touches.get(filename) or GETMTINE(filename))


class TestJavascriptAssetsBundle(FileTouchable):
    def setUp(self):
        super(TestJavascriptAssetsBundle, self).setUp()
        self.jsbundle_name = 'test_assetsbundle.bundle1'
        self.cssbundle_name = 'test_assetsbundle.bundle2'
        self.env['res.lang']._activate_lang('ar_SY')

    def _get_asset(self, bundle, env=None):
        env = (env or self.env)
        files, _ = env['ir.qweb']._get_asset_content(bundle)
        return AssetsBundle(bundle, files, env=env)

    def _any_ira_for_bundle(self, extension, lang=None):
        """ Returns all ir.attachments associated to a bundle, regardless of the verion.
        """
        user_direction = self.env['res.lang']._lang_get(lang or self.env.user.lang).direction
        bundle = self.jsbundle_name if extension in ['js', 'min.js'] else self.cssbundle_name
        rtl = 'rtl/' if extension in ['css', 'min.css'] and user_direction == 'rtl' else ''
        url = f'/web/assets/%-%/{rtl}{bundle}.{extension}'
        domain = [('url', '=like', url)]
        return self.env['ir.attachment'].search(domain)

    def _node_to_list(self, nodes):
        res = []
        for index, (tagName, t_attrs, content) in enumerate(nodes):
            for name, value in t_attrs.items():
                res.append(value)
        return res

    def test_01_generation(self):
        """ Checks that a bundle creates an ir.attachment record when its `js` method is called
        for the first time and this ir.attachment is different depending on `is_minified` param.
        """
        self.bundle = self._get_asset(self.jsbundle_name, env=self.env)

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

        version0 = bundle0.version
        ira0 = self._any_ira_for_bundle('min.js')
        date0 = ira0.create_date

        bundle1 = self._get_asset(self.jsbundle_name)
        bundle1.js()

        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified attachment associated to this bundle")

        version1 = bundle1.version
        ira1 = self._any_ira_for_bundle('min.js')
        date1 = ira1.create_date

        self.assertEqual(version0, version1,
                         "the version should not be changed because the bundle hasn't changed")
        self.assertEqual(date0, date1,
                         "the date of creation of the ir.attachment should not change because the bundle is unchanged")

    def test_03_date_invalidation(self):
        """ Checks that a bundle is invalidated when one of its assets' modification date is changed.
        """
        bundle0 = self._get_asset(self.jsbundle_name)
        bundle0.js()
        last_modified0 = bundle0.last_modified_combined
        version0 = bundle0.version

        path = get_resource_path('test_assetsbundle', 'static', 'src', 'js', 'test_jsfile1.js')
        bundle1 = self._get_asset(self.jsbundle_name)

        with self._touch(path):
            bundle1.js()
            last_modified1 = bundle1.last_modified_combined
            version1 = bundle1.version
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
        version0 = bundle0.version

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
        version1 = bundle1.version

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
        nodes = debug_bundle.to_node()
        content = self._node_to_list(nodes)
        # there should be a minified file
        self.assertEqual(content[3].count('test_assetsbundle.bundle1.min.js'), 1)

        # there should be one minified assets created in normal mode
        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified assets created in normal mode")

        # there shouldn't be any non-minified assets created in normal mode
        self.assertEqual(len(self._any_ira_for_bundle('js')), 0,
                         "there shouldn't be any non-minified assets created in normal mode")

    def test_06_debug(self):
        """ Checks that a bundle rendered in debug 1 mode outputs non-minified assets
            and create an non-minified ir.attachment.
        """
        debug_bundle = self._get_asset(self.jsbundle_name)
        nodes = debug_bundle.to_node(debug='1')
        content = self._node_to_list(nodes)
        # there should be a minified file
        self.assertEqual(content[3].count('test_assetsbundle.bundle1.min.js'), 1,
                         "there should be one minified assets created in debug mode")

        # there should be one minified assets created in debug mode
        self.assertEqual(len(self._any_ira_for_bundle('min.js')), 1,
                         "there should be one minified assets created in debug mode")

        # there shouldn't be any non-minified assets created in debug mode
        self.assertEqual(len(self._any_ira_for_bundle('js')), 0,
                         "there shouldn't be any non-minified assets created in debug mode")

    def test_07_debug_assets(self):
        """ Checks that a bundle rendered in debug assets mode outputs non-minified assets
            and create an non-minified ir.attachment at the .
        """
        debug_bundle = self._get_asset(self.jsbundle_name)
        nodes = debug_bundle.to_node(debug='assets')
        content = self._node_to_list(nodes)
        # there should be a non-minified file (not .min.js)
        self.assertEqual(content[3].count('test_assetsbundle.bundle1.js'), 1,
                         "there should be one non-minified assets created in debug assets mode")

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

        version0 = bundle0.version
        ira0 = self._any_ira_for_bundle('min.css')
        date0 = ira0.create_date

        bundle1 = self._get_asset(self.cssbundle_name)
        bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        version1 = bundle1.version
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
        version0 = bundle0.version

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        self.env['ir.asset'].create({
            'name': 'test bundle inheritance',
            'bundle': self.cssbundle_name,
            'path': 'test_assetsbundle/static/src/css/test_cssfile2.css',
        })

        bundle1 = self._get_asset(self.cssbundle_name)
        bundle1.css()
        files1 = bundle1.files
        version1 = bundle1.version

        self.assertNotEqual(files0, files1)
        self.assertNotEqual(version0, version1)

        # check if the previous attachment are correctly cleaned
        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

    def test_12_css_debug(self):
        """ Check that a bundle in debug mode outputs non-minified assets.
        """
        debug_bundle = self._get_asset(self.cssbundle_name)
        nodes = debug_bundle.to_node(debug='assets')
        content = self._node_to_list(nodes)
        # find back one of the original asset file
        self.assertIn('/web/assets/debug/test_assetsbundle.bundle2.css', content)

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
        nodes = bundle0.to_node()
        content = self._node_to_list(nodes)
        self.assertEqual(content[2].count('test_assetsbundle.bundle2.min.css'), 1)

    # Language direction specific tests

    def test_15_rtl_css_generation(self):
        """ Checks that a bundle creates an ir.attachment record when its `css` method is called
        for the first time for language with different direction and separate bundle is created for rtl direction.
        """
        self.bundle = self._get_asset(self.cssbundle_name, env=self.env(context={'lang': 'ar_SY'}))

        # there shouldn't be any attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('min.css', lang='ar_SY')), 0)
        self.assertEqual(len(self.bundle.get_attachments('min.css')), 0)

        # trigger the first generation and, thus, the first save in database
        self.bundle.css()

        # there should be no compilation errors
        self.assertEqual(len(self.bundle.css_errors), 0)

        # there should be one attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('min.css', lang='ar_SY')), 1)
        self.assertEqual(len(self.bundle.get_attachments('min.css')), 1)

    def test_15_rtl_invalid_css_generation(self):
        """ Checks that erroneous css cannot be compiled by rtlcss and that errors are registered """
        self.bundle = self._get_asset('test_assetsbundle.broken_css', env=self.env(context={'lang': 'ar_SY'}))
        with mute_logger('odoo.addons.base.models.assetsbundle'):
            self.bundle.css()
        self.assertEqual(len(self.bundle.css_errors), 1)
        self.assertIn('rtlcss: error processing payload', self.bundle.css_errors[0])

    def test_16_ltr_and_rtl_css_access(self):
        """ Checks that the bundle's cache is working, i.e. that the bundle creates only one
        ir.attachment record when rendered multiple times for rtl direction also check we have two css bundles,
        one for ltr and one for rtl.
        """
        # Assets access for en_US language
        ltr_bundle0 = self._get_asset(self.cssbundle_name)
        ltr_bundle0.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        ltr_version0 = ltr_bundle0.version
        ltr_ira0 = self._any_ira_for_bundle('min.css')
        ltr_date0 = ltr_ira0.create_date

        ltr_bundle1 = self._get_asset(self.cssbundle_name)
        ltr_bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css')), 1)

        ltr_version1 = ltr_bundle1.version
        ltr_ira1 = self._any_ira_for_bundle('min.css')
        ltr_date1 = ltr_ira1.create_date

        self.assertEqual(ltr_version0, ltr_version1)
        self.assertEqual(ltr_date0, ltr_date1)

        # Assets access for ar_SY language
        rtl_bundle0 = self._get_asset(self.cssbundle_name, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle0.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css', lang='ar_SY')), 1)

        rtl_version0 = rtl_bundle0.version
        rtl_ira0 = self._any_ira_for_bundle('min.css', lang='ar_SY')
        rtl_date0 = rtl_ira0.create_date

        rtl_bundle1 = self._get_asset(self.cssbundle_name, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('min.css', lang='ar_SY')), 1)

        rtl_version1 = rtl_bundle1.version
        rtl_ira1 = self._any_ira_for_bundle('min.css', lang='ar_SY')
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
        # Assets access for en_US language
        ltr_bundle0 = self._get_asset(self.cssbundle_name)
        ltr_bundle0.css()
        ltr_last_modified0 = ltr_bundle0.last_modified_combined
        ltr_version0 = ltr_bundle0.version

        # Assets access for ar_SY language
        rtl_bundle0 = self._get_asset(self.cssbundle_name, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle0.css()
        rtl_last_modified0 = rtl_bundle0.last_modified_combined
        rtl_version0 = rtl_bundle0.version

        # Touch test_cssfile1.css
        # Note: No lang specific context given while calling _get_asset so it will load assets for en_US
        path = get_resource_path('test_assetsbundle', 'static', 'src', 'css', 'test_cssfile1.css')
        ltr_bundle1 = self._get_asset(self.cssbundle_name)

        with self._touch(path):
            ltr_bundle1.css()
            ltr_last_modified1 = ltr_bundle1.last_modified_combined
            ltr_version1 = ltr_bundle1.version
            ltr_ira1 = self._any_ira_for_bundle('min.css')
            self.assertNotEqual(ltr_last_modified0, ltr_last_modified1)
            self.assertNotEqual(ltr_version0, ltr_version1)

            rtl_bundle1 = self._get_asset(self.cssbundle_name, env=self.env(context={'lang': 'ar_SY'}))

            rtl_bundle1.css()
            rtl_last_modified1 = rtl_bundle1.last_modified_combined
            rtl_version1 = rtl_bundle1.version
            rtl_ira1 = self._any_ira_for_bundle('min.css', lang='ar_SY')
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
        ltr_version0 = ltr_bundle0.version

        rtl_bundle0 = self._get_asset(self.cssbundle_name, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle0.css()
        rtl_files0 = rtl_bundle0.files
        rtl_version0 = rtl_bundle0.version

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
        ltr_version1 = ltr_bundle1.version
        ltr_ira1 = self._any_ira_for_bundle('min.css')

        self.assertNotEqual(ltr_files0, ltr_files1)
        self.assertNotEqual(ltr_version0, ltr_version1)

        rtl_bundle1 = self._get_asset(self.cssbundle_name, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle1.css()
        rtl_files1 = rtl_bundle1.files
        rtl_version1 = rtl_bundle1.version
        rtl_ira1 = self._any_ira_for_bundle('min.css', lang='ar_SY')

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
        debug_bundle = self._get_asset(self.cssbundle_name, env=self.env(context={'lang': 'ar_SY'}))
        nodes = debug_bundle.to_node(debug='assets')
        content = self._node_to_list(nodes)

        # there should be an css assets bundle in /debug/rtl if user's lang direction is rtl and debug=assets
        self.assertIn('/web/assets/debug/rtl/{0}.css'.format(self.cssbundle_name), content,
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

        asset_data_css = etree.HTML(html).xpath('//*[@data-asset-bundle]')[0]
        asset_data_js = etree.HTML(html).xpath('//*[@data-asset-bundle]')[1]

        format_data = {
            "js": attachments[0].url,
            "css": attachments[1].url,
            "asset_bundle_css": asset_data_css.attrib.get('data-asset-bundle'),
            "asset_version_css": asset_data_css.attrib.get('data-asset-version'),
            "asset_bundle_js": asset_data_js.attrib.get('data-asset-bundle'),
            "asset_version_js": asset_data_js.attrib.get('data-asset-version'),

        }

        self.assertEqual(html.strip(), ("""<!DOCTYPE html>
<html>
    <head>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="%(css)s" data-asset-bundle="%(asset_bundle_css)s" data-asset-version="%(asset_version_css)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="%(js)s" data-asset-bundle="%(asset_bundle_js)s" data-asset-version="%(asset_version_js)s"></script>
    </head>
    <body>
    </body>
</html>""" % format_data))

    def test_21_external_lib_assets_debug_mode(self):
        html = self.env['ir.ui.view']._render_template('test_assetsbundle.template2', {"debug": "assets"})
        attachments = self.env['ir.attachment'].search([('url', '=like', '%/test_assetsbundle.bundle4.js')])
        self.assertEqual(len(attachments), 1)

        asset_data_css = etree.HTML(html).xpath('//*[@data-asset-bundle]')[0]
        asset_data_js = etree.HTML(html).xpath('//*[@data-asset-bundle]')[1]

        format_data = {
            "asset_bundle_css": asset_data_css.attrib.get('data-asset-bundle'),
            "asset_version_css": asset_data_css.attrib.get('data-asset-version'),
            "asset_bundle_js": asset_data_js.attrib.get('data-asset-bundle'),
            "asset_version_js": asset_data_js.attrib.get('data-asset-version'),
            "css": '/web/assets/debug/test_assetsbundle.bundle4.css',
            "js": '/web/assets/debug/test_assetsbundle.bundle4.js',
        }
        self.assertEqual(html.strip(), ("""<!DOCTYPE html>
<html>
    <head>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="%(css)s" data-asset-bundle="%(asset_bundle_css)s" data-asset-version="%(asset_version_css)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="%(js)s" data-asset-bundle="%(asset_bundle_js)s" data-asset-version="%(asset_version_js)s"></script>
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
        files, _ = self.env['ir.qweb']._get_asset_content(self.stylebundle_name)
        return AssetsBundle(self.stylebundle_name, files, env=self.env)

    def _bundle(self, asset, should_create, should_unlink):
        self.counter.clear()
        asset.to_node(debug='assets')
        self.assertEqual(self.counter['create'], 2 if should_create else 0)
        self.assertEqual(self.counter['unlink'], 2 if should_unlink else 0)

    def test_01_debug_mode_assets(self):
        """ Checks that the ir.attachments records created for compiled assets in debug mode
        are correctly invalidated.
        """
        # Compile for the first time
        self._bundle(self._get_asset(), True, False)

        # Compile a second time, without changes
        self._bundle(self._get_asset(), False, False)

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
            'path': 'test_assetsbundle/static/src/**/*',
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

    def test_20_css_compatibility_prefix(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irasset2',
            'path': 'test_assetsbundle/static/src/scss/test_prefix.scss',
        })
        view = self.make_asset_view('test_assetsbundle.irasset2', {
            't-js': 'false',
            't-css': 'true',
        })
        self.env['ir.qweb']._render(view.id)
        attach = self.env['ir.attachment'].search([('name', 'ilike', 'test_assetsbundle.irasset2')], order='create_date DESC', limit=1)
        content = attach.raw.decode()
        print("=" * 78) # DEBUG
        print(content)  # DEBUG
        print("=" * 78) # DEBUG
        self.assertRegex(content, '.appearance-none{-webkit-appearance: none; -moz-appearance: none; appearance: none;}')
        self.assertRegex(content, '.appearance-auto{-webkit-appearance: auto; -moz-appearance: auto; appearance: auto;}')
        self.assertRegex(content, '.appearance-none-prefixed{-webkit-appearance: none;}')

        self.assertRegex(content, '.display-flex{display: -webkit-box; display: -webkit-flex; display: flex;}')
        self.assertRegex(content, '.display-inline-flex{display: -webkit-inline-box; display: -webkit-inline-flex; display: inline-flex;}')
        self.assertRegex(content, '.display-inline{display: inline;}')        
        self.assertRegex(content, '.display-var-flex{--dummy-display: flex;}')
        self.assertRegex(content, '.display-var-inline-flex{--dummy-display: inline-flex;}')
        self.assertRegex(content, '.display-var-inline{--dummy-display: inline;}')

        self.assertRegex(content, '.flex-flow-row-nowrap{-webkit-flex-flow: row nowrap; flex-flow: row nowrap;}')
        self.assertRegex(content, '.flex-flow-column-wrap{-webkit-flex-flow: column wrap; flex-flow: column wrap;}')
        self.assertRegex(content, '.flex-flow-column-reverse-wrap-reverse{flex-flow: column-reverse wrap-reverse;}')
        self.assertRegex(content, '.flex-flow-row{flex-flow: row;}')
        
        self.assertRegex(content, '.flex-direction-column{-webkit-box-orient: vertical; -webkit-box-direction: normal; -webkit-flex-direction: column; flex-direction: column;}')
        self.assertRegex(content, '.flex-direction-column-reverse{flex-direction: column-reverse;}')
        self.assertRegex(content, '.flex-direction-row{flex-direction: row;}')
        
        self.assertRegex(content, '.flex-wrap-wrap{-webkit-flex-wrap: wrap; flex-wrap: wrap;}')
        self.assertRegex(content, '.flex-wrap-nowrap{-webkit-flex-wrap: nowrap; flex-wrap: nowrap;}')
        self.assertRegex(content, '.flex-wrap-wrap-reverse{flex-wrap: wrap-reverse;}')

        self.assertRegex(content, '.flex-0-0-auto{-webkit-box-flex: 0; -webkit-flex: 0 0 auto; flex: 0 0 auto;}')
        self.assertRegex(content, '.flex-0-1-auto{-webkit-box-flex: 0; -webkit-flex: 0 1 auto; flex: 0 1 auto;}')
        self.assertRegex(content, '.flex-1-1-100{-webkit-box-flex: 1; -webkit-flex: 1 1 100; flex: 1 1 100;}')
        self.assertRegex(content, '.flex-1-1-100percent{flex: 1 1 100%;}')
        self.assertRegex(content, '.flex-auto{flex: auto;}')
        self.assertRegex(content, '.flex-1-30px{flex: 1 30px;}')

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
        self.assertFalse(attach.exists())

    @mute_logger('odoo.addons.base.models.ir_asset')
    def test_32(self):
        path_to_dummy = '../../tests/dummy.xml'
        me = pathlib.Path(__file__).parent.absolute()
        file_path = me.joinpath("..", path_to_dummy)  # assuming me = test_assetsbundle/tests
        self.assertTrue(os.path.isfile(file_path))

        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/test_assetsbundle/%s' % path_to_dummy,
        })

        files = self.env['ir.asset']._get_asset_paths('test_assetsbundle.irassetsec', addons=list(self.installed_modules))
        self.assertFalse(files)

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
        files = self.env['ir.asset']._get_asset_paths('test_assetsbundle.irassetsec', addons=list(self.installed_modules))
        self.assertFalse(files)

    def test_36(self):
        self.env['ir.asset'].create({
            'name': '1',
            'bundle': 'test_assetsbundle.irassetsec',
            'path': '/test_assetsbundle/static/accessible.xml',
        })
        files = self.env['ir.asset']._get_asset_paths('test_assetsbundle.irassetsec', addons=list(self.installed_modules))
        self.assertEqual(len(files), 1)
        self.assertTrue('test_assetsbundle/static/accessible.xml' in files[0][0])

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
