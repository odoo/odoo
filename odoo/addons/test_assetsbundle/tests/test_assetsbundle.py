# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
import datetime
import errno
from lxml import etree
import os
import time
from unittest.mock import patch

from odoo import api
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.modules.module import get_resource_path
from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase

GETMTINE = os.path.getmtime


class FileTouchable(TransactionCase):
    def setUp(self):
        super(FileTouchable, self).setUp()
        self.touches = {}

    def _touch(self, filepath, touch_time=None):
        self.touches[filepath] = touch_time or time.time()
        return patch('os.path.getmtime', lambda filename: self.touches.get(filename) or GETMTINE(filename))


class TestJavascriptAssetsBundle(FileTouchable):
    def setUp(self):
        super(TestJavascriptAssetsBundle, self).setUp()
        self.jsbundle_xmlid = 'test_assetsbundle.bundle1'
        self.cssbundle_xmlid = 'test_assetsbundle.bundle2'
        self.env['res.lang']._activate_lang('ar_SY')


    def _get_asset(self, xmlid, env=None):
        env = (env or self.env)
        files, remains = env['ir.qweb']._get_asset_content(xmlid, env.context)
        return AssetsBundle(xmlid, files, env=env)

    def _any_ira_for_bundle(self, type, lang=None):
        """ Returns all ir.attachments associated to a bundle, regardless of the verion.
        """
        user_direction = self.env['res.lang']._lang_get(lang or self.env.user.lang).direction
        bundle = self.jsbundle_xmlid if type == 'js' else self.cssbundle_xmlid
        url = '/web/content/%-%/{0}{1}.{2}'.format(('rtl/' if type == 'css' and user_direction == 'rtl' else ''), bundle, type)
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
        for the first time.
        """
        self.bundle = self._get_asset(self.jsbundle_xmlid, env=self.env)

        # there shouldn't be any attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('js')), 0)
        self.assertEqual(len(self.bundle.get_attachments('js')), 0)

        # trigger the first generation and, thus, the first save in database
        self.bundle.js()

        # there should be one attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('js')), 1)
        self.assertEqual(len(self.bundle.get_attachments('js')), 1)

    def test_02_access(self):
        """ Checks that the bundle's cache is working, i.e. that the bundle creates only one
        ir.attachment record when rendered multiple times.
        """
        bundle0 = self._get_asset(self.jsbundle_xmlid)
        bundle0.js()

        self.assertEqual(len(self._any_ira_for_bundle('js')), 1)

        version0 = bundle0.version
        ira0 = self._any_ira_for_bundle('js')
        date0 = ira0.create_date

        bundle1 = self._get_asset(self.jsbundle_xmlid)
        bundle1.js()

        self.assertEqual(len(self._any_ira_for_bundle('js')), 1)

        version1 = bundle1.version
        ira1 = self._any_ira_for_bundle('js')
        date1 = ira1.create_date

        self.assertEqual(version0, version1)
        self.assertEqual(date0, date1)

    def test_03_date_invalidation(self):
        """ Checks that a bundle is invalidated when one of its assets' modification date is changed.
        """
        bundle0 = self._get_asset(self.jsbundle_xmlid)
        bundle0.js()
        last_modified0 = bundle0.last_modified
        version0 = bundle0.version

        path = get_resource_path('test_assetsbundle', 'static', 'src', 'js', 'test_jsfile1.js')
        bundle1 = self._get_asset(self.jsbundle_xmlid)

        with self._touch(path):
            bundle1.js()
            last_modified1 = bundle1.last_modified
            version1 = bundle1.version
            self.assertNotEqual(last_modified0, last_modified1)
            self.assertNotEqual(version0, version1)

            # check if the previous attachment is correctly cleaned
            self.assertEqual(len(self._any_ira_for_bundle('js')), 1)

    def test_04_content_invalidation(self):
        """ Checks that a bundle is invalidated when its content is modified by adding a file to
        source.
        """
        bundle0 = self._get_asset(self.jsbundle_xmlid)
        bundle0.js()
        files0 = bundle0.files
        version0 = bundle0.version

        self.assertEqual(len(self._any_ira_for_bundle('js')), 1)

        view_arch = """
        <data>
            <xpath expr="." position="inside">
                <script type="text/javascript" src="/test_assetsbundle/static/src/js/test_jsfile4.js"/>
            </xpath>
        </data>
        """
        bundle = self.browse_ref(self.jsbundle_xmlid)
        view = self.env['ir.ui.view'].create({
            'name': 'test bundle inheritance',
            'type': 'qweb',
            'arch': view_arch,
            'inherit_id': bundle.id,
        })

        bundle1 = self._get_asset(self.jsbundle_xmlid, env=self.env(context={'check_view_ids': view.ids}))
        bundle1.js()
        files1 = bundle1.files
        version1 = bundle1.version

        self.assertNotEqual(files0, files1)
        self.assertNotEqual(version0, version1)

        # check if the previous attachment are correctly cleaned
        self.assertEqual(len(self._any_ira_for_bundle('js')), 1)

    def test_05_debug(self):
        """ Checks that a bundle rendered in debug mode outputs non-minified assets.
        """
        debug_bundle = self._get_asset(self.jsbundle_xmlid)
        nodes = debug_bundle.to_node(debug='assets')
        content = self._node_to_list(nodes)
        # find back one of the original asset file
        self.assertIn('/test_assetsbundle/static/src/js/test_jsfile1.js', content)

        # there shouldn't be any assets created in debug mode
        self.assertEqual(len(self._any_ira_for_bundle('js')), 0)

    def test_08_css_generation3(self):
        # self.cssbundle_xlmid contains 3 rules
        self.bundle = self._get_asset(self.cssbundle_xmlid)
        self.bundle.css()
        self.assertEqual(len(self._any_ira_for_bundle('css')), 1)
        self.assertEqual(len(self.bundle.get_attachments('css')), 1)

    def test_09_css_access(self):
        """ Checks that the bundle's cache is working, i.e. that a bundle creates only enough
        ir.attachment records when rendered multiple times.
        """
        bundle0 = self._get_asset(self.cssbundle_xmlid)
        bundle0.css()

        self.assertEqual(len(self._any_ira_for_bundle('css')), 1)

        version0 = bundle0.version
        ira0 = self._any_ira_for_bundle('css')
        date0 = ira0.create_date

        bundle1 = self._get_asset(self.cssbundle_xmlid)
        bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('css')), 1)

        version1 = bundle1.version
        ira1 = self._any_ira_for_bundle('css')
        date1 = ira1.create_date

        self.assertEqual(version0, version1)
        self.assertEqual(date0, date1)

    def test_11_css_content_invalidation(self):
        """ Checks that a bundle is invalidated when its content is modified by adding a file to
        source.
        """
        bundle0 = self._get_asset(self.cssbundle_xmlid)
        bundle0.css()
        files0 = bundle0.files
        version0 = bundle0.version

        self.assertEqual(len(self._any_ira_for_bundle('css')), 1)

        view_arch = """
        <data>
            <xpath expr="." position="inside">
                <link rel="stylesheet" href="/test_assetsbundle/static/src/css/test_cssfile2.css"/>
            </xpath>
        </data>
        """
        bundle = self.browse_ref(self.cssbundle_xmlid)
        view = self.env['ir.ui.view'].create({
            'name': 'test bundle inheritance',
            'type': 'qweb',
            'arch': view_arch,
            'inherit_id': bundle.id,
        })

        bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'check_view_ids': view.ids}))
        bundle1.css()
        files1 = bundle1.files
        version1 = bundle1.version

        self.assertNotEqual(files0, files1)
        self.assertNotEqual(version0, version1)

        # check if the previous attachment are correctly cleaned
        self.assertEqual(len(self._any_ira_for_bundle('css')), 1)

    def test_12_css_debug(self):
        """ Check that a bundle in debug mode outputs non-minified assets.
        """
        debug_bundle = self._get_asset(self.cssbundle_xmlid)
        nodes = debug_bundle.to_node(debug='assets')
        content = self._node_to_list(nodes)
        # find back one of the original asset file
        self.assertIn('/test_assetsbundle/static/src/css/test_cssfile1.css', content)

        # there shouldn't be any assets created in debug mode
        self.assertEqual(len(self._any_ira_for_bundle('css')), 0)

    def test_14_duplicated_css_assets(self):
        """ Checks that if the bundle's ir.attachment record is duplicated, the bundle is only sourced once. This could
        happen if multiple transactions try to render the bundle simultaneously.
        """
        bundle0 = self._get_asset(self.cssbundle_xmlid)
        bundle0.css()
        self.assertEqual(len(self._any_ira_for_bundle('css')), 1)

        # duplicate the asset bundle
        ira0 = self._any_ira_for_bundle('css')
        ira1 = ira0.copy()
        self.assertEqual(len(self._any_ira_for_bundle('css')), 2)
        self.assertEqual(ira0.store_fname, ira1.store_fname)

        # the ir.attachment records should be deduplicated in the bundle's content
        nodes = bundle0.to_node()
        content = self._node_to_list(nodes)
        self.assertEqual(content[2].count('test_assetsbundle.bundle2.css'), 1)

    # Language direction specific tests

    def test_15_rtl_css_generation(self):
        """ Checks that a bundle creates an ir.attachment record when its `css` method is called
        for the first time for language with different direction and separate bundle is created for rtl direction.
        """
        self.bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))

        # there shouldn't be any attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('css', lang='ar_SY')), 0)
        self.assertEqual(len(self.bundle.get_attachments('css')), 0)

        # trigger the first generation and, thus, the first save in database
        self.bundle.css()

        # there should be one attachment associated to this bundle
        self.assertEqual(len(self._any_ira_for_bundle('css', lang='ar_SY')), 1)
        self.assertEqual(len(self.bundle.get_attachments('css')), 1)

    def test_16_ltr_and_rtl_css_access(self):
        """ Checks that the bundle's cache is working, i.e. that the bundle creates only one
        ir.attachment record when rendered multiple times for rtl direction also check we have two css bundles,
        one for ltr and one for rtl.
        """
        # Assets access for en_US language
        ltr_bundle0 = self._get_asset(self.cssbundle_xmlid)
        ltr_bundle0.css()

        self.assertEqual(len(self._any_ira_for_bundle('css')), 1)

        ltr_version0 = ltr_bundle0.version
        ltr_ira0 = self._any_ira_for_bundle('css')
        ltr_date0 = ltr_ira0.create_date

        ltr_bundle1 = self._get_asset(self.cssbundle_xmlid)
        ltr_bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('css')), 1)

        ltr_version1 = ltr_bundle1.version
        ltr_ira1 = self._any_ira_for_bundle('css')
        ltr_date1 = ltr_ira1.create_date

        self.assertEqual(ltr_version0, ltr_version1)
        self.assertEqual(ltr_date0, ltr_date1)

        # Assets access for ar_SY language
        rtl_bundle0 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle0.css()

        self.assertEqual(len(self._any_ira_for_bundle('css', lang='ar_SY')), 1)

        rtl_version0 = rtl_bundle0.version
        rtl_ira0 = self._any_ira_for_bundle('css', lang='ar_SY')
        rtl_date0 = rtl_ira0.create_date

        rtl_bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle1.css()

        self.assertEqual(len(self._any_ira_for_bundle('css', lang='ar_SY')), 1)

        rtl_version1 = rtl_bundle1.version
        rtl_ira1 = self._any_ira_for_bundle('css', lang='ar_SY')
        rtl_date1 = rtl_ira1.create_date

        self.assertEqual(rtl_version0, rtl_version1)
        self.assertEqual(rtl_date0, rtl_date1)

        # Checks rtl and ltr bundles are different
        self.assertNotEqual(ltr_ira1.id, rtl_ira1.id)

        # Check two bundles are available, one for ltr and one for rtl
        css_bundles = self.env['ir.attachment'].search([
            ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(self.cssbundle_xmlid, 'css'))
        ])
        self.assertEqual(len(css_bundles), 2)

    def test_17_css_bundle_date_invalidation(self):
        """ Checks that both css bundles are invalidated when one of its assets' modification date is changed
        """
        # Assets access for en_US language
        ltr_bundle0 = self._get_asset(self.cssbundle_xmlid)
        ltr_bundle0.css()
        ltr_last_modified0 = ltr_bundle0.last_modified
        ltr_version0 = ltr_bundle0.version

        # Assets access for ar_SY language
        rtl_bundle0 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle0.css()
        rtl_last_modified0 = rtl_bundle0.last_modified
        rtl_version0 = rtl_bundle0.version

        # Touch test_cssfile1.css
        # Note: No lang specific context given while calling _get_asset so it will load assets for en_US
        path = get_resource_path('test_assetsbundle', 'static', 'src', 'css', 'test_cssfile1.css')
        ltr_bundle1 = self._get_asset(self.cssbundle_xmlid)

        with self._touch(path):
            ltr_bundle1.css()
            ltr_last_modified1 = ltr_bundle1.last_modified
            ltr_version1 = ltr_bundle1.version
            ltr_ira1 = self._any_ira_for_bundle('css')
            self.assertNotEqual(ltr_last_modified0, ltr_last_modified1)
            self.assertNotEqual(ltr_version0, ltr_version1)

            rtl_bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))

            rtl_bundle1.css()
            rtl_last_modified1 = rtl_bundle1.last_modified
            rtl_version1 = rtl_bundle1.version
            rtl_ira1 = self._any_ira_for_bundle('css', lang='ar_SY')
            self.assertNotEqual(rtl_last_modified0, rtl_last_modified1)
            self.assertNotEqual(rtl_version0, rtl_version1)

            # Checks rtl and ltr bundles are different
            self.assertNotEqual(ltr_ira1.id, rtl_ira1.id)

            # check if the previous attachment is correctly cleaned
            css_bundles = self.env['ir.attachment'].search([
                ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(self.cssbundle_xmlid, 'css'))
            ])
            self.assertEqual(len(css_bundles), 2)

    def test_18_css_bundle_content_invalidation(self):
        """ Checks that a bundle is invalidated when its content is modified by adding a file to
        source.
        """
        # Assets for en_US
        ltr_bundle0 = self._get_asset(self.cssbundle_xmlid)
        ltr_bundle0.css()
        ltr_files0 = ltr_bundle0.files
        ltr_version0 = ltr_bundle0.version

        rtl_bundle0 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle0.css()
        rtl_files0 = rtl_bundle0.files
        rtl_version0 = rtl_bundle0.version

        css_bundles = self.env['ir.attachment'].search([
            ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(self.cssbundle_xmlid, 'css'))
        ])
        self.assertEqual(len(css_bundles), 2)

        view_arch = """
        <data>
            <xpath expr="." position="inside">
                <script type="text/css" src="/test_assetsbundle/static/src/css/test_cssfile3.css"/>
            </xpath>
        </data>
        """
        bundle = self.browse_ref(self.cssbundle_xmlid)
        view = self.env['ir.ui.view'].create({
            'name': 'test bundle inheritance',
            'type': 'qweb',
            'arch': view_arch,
            'inherit_id': bundle.id,
        })

        ltr_bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'check_view_ids': view.ids}))
        ltr_bundle1.css()
        ltr_files1 = ltr_bundle1.files
        ltr_version1 = ltr_bundle1.version
        ltr_ira1 = self._any_ira_for_bundle('css')

        self.assertNotEqual(ltr_files0, ltr_files1)
        self.assertNotEqual(ltr_version0, ltr_version1)

        rtl_bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'check_view_ids': view.ids, 'lang': 'ar_SY'}))
        rtl_bundle1.css()
        rtl_files1 = rtl_bundle1.files
        rtl_version1 = rtl_bundle1.version
        rtl_ira1 = self._any_ira_for_bundle('css', lang='ar_SY')

        self.assertNotEqual(rtl_files0, rtl_files1)
        self.assertNotEqual(rtl_version0, rtl_version1)

        # Checks rtl and ltr bundles are different
        self.assertNotEqual(ltr_ira1.id, rtl_ira1.id)

        # check if the previous attachment are correctly cleaned
        css_bundles = self.env['ir.attachment'].search([
            ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(self.cssbundle_xmlid, 'css'))
        ])
        self.assertEqual(len(css_bundles), 2)

    def test_19_css_in_debug_assets(self):
        """ Checks that a bundle rendered in debug mode(assets) with right to left language direction stores css files in assets bundle.
        """
        debug_bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))
        nodes = debug_bundle.to_node(debug='assets')
        content = self._node_to_list(nodes)

        # css file should be available in assets bundle as user's lang direction is rtl
        self.assertIn('/test_assetsbundle/static/src/css/test_cssfile1/rtl/{0}.css'.format(self.cssbundle_xmlid), content)

        # there should be assets(css) created in debug mode as user's lang direction is rtl
        css_bundle = self.env['ir.attachment'].search([
            ('url', '=', '/test_assetsbundle/static/src/css/test_cssfile1/rtl/{0}.css'.format(self.cssbundle_xmlid))
        ])
        self.assertEqual(len(css_bundle), 1)

    def test_20_exteral_lib_assets(self):
        html = self.env['ir.ui.view']._render_template('test_assetsbundle.template2')
        attachments = self.env['ir.attachment'].search([('url', '=like', '/web/content/%-%/test_assetsbundle.bundle4.%')])
        self.assertEqual(len(attachments), 2)

        asset_data = etree.HTML(html).xpath('//*[@data-asset-xmlid]')[0]
        asset_xmlid = asset_data.attrib.get('data-asset-xmlid')
        asset_version = asset_data.attrib.get('data-asset-version')

        format_data = {
            "js": attachments[0].url,
            "css": attachments[1].url,
            "asset_xmlid": asset_xmlid,
            "asset_version": asset_version,
        }

        self.assertEqual(html.strip(), ("""<!DOCTYPE html>
<html>
    <head>
        <link rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="%(css)s" data-asset-xmlid="%(asset_xmlid)s" data-asset-version="%(asset_version)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="%(js)s" data-asset-xmlid="%(asset_xmlid)s" data-asset-version="%(asset_version)s"></script>
    </head>
    <body>
    </body>
</html>""" % format_data).encode('utf8'))

    def test_21_exteral_lib_assets_debug_mode(self):
        html = self.env['ir.ui.view']._render_template('test_assetsbundle.template2', {"debug": "assets"})
        attachments = self.env['ir.attachment'].search([('url', '=like', '/web/content/%-%/test_assetsbundle.bundle4.%')])
        self.assertEqual(len(attachments), 0)

        asset_data = etree.HTML(html).xpath('//*[@data-asset-xmlid]')[0]
        asset_xmlid = asset_data.attrib.get('data-asset-xmlid')
        asset_version = asset_data.attrib.get('data-asset-version')

        format_data = {
            "asset_xmlid": asset_xmlid,
            "asset_version": asset_version,
        }

        self.assertEqual(html.strip(), ("""<!DOCTYPE html>
<html>
    <head>
        <link rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="/test_assetsbundle/static/src/css/test_cssfile1.css" data-asset-xmlid="%(asset_xmlid)s" data-asset-version="%(asset_version)s"/>
        <link type="text/css" rel="stylesheet" href="/test_assetsbundle/static/src/css/test_cssfile2.css" data-asset-xmlid="%(asset_xmlid)s" data-asset-version="%(asset_version)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="/test_assetsbundle/static/src/js/test_jsfile1.js" data-asset-xmlid="%(asset_xmlid)s" data-asset-version="%(asset_version)s"></script>
        <script type="text/javascript" src="/test_assetsbundle/static/src/js/test_jsfile2.js" data-asset-xmlid="%(asset_xmlid)s" data-asset-version="%(asset_version)s"></script>
        <script type="text/javascript" src="/test_assetsbundle/static/src/js/test_jsfile3.js" data-asset-xmlid="%(asset_xmlid)s" data-asset-version="%(asset_version)s"></script>
    </head>
    <body>
    </body>
</html>""" % format_data).encode('utf8'))


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
        self.env.user.flush()

        self.browser_js(
            "/test_assetsbundle/js",
            "a + b + c + d === 10 ? console.log('test successful') : console.log('error')",
            login="admin",
        )


class TestAssetsBundleWithIRAMock(FileTouchable):
    def setUp(self):
        super(TestAssetsBundleWithIRAMock, self).setUp()
        self.stylebundle_xmlid = 'test_assetsbundle.bundle3'
        self.counter = counter = Counter()

        # patch methods 'create' and 'unlink' of model 'ir.attachment'
        origin_create = IrAttachment.create
        origin_unlink = IrAttachment.unlink

        @api.model
        def create(self, vals):
            counter.update(['create'])
            return origin_create(self, vals)

        def unlink(self):
            counter.update(['unlink'])
            return origin_unlink(self)

        self.patch(IrAttachment, 'create', create)
        self.patch(IrAttachment, 'unlink', unlink)

    def _get_asset(self):
        files, remains = self.env['ir.qweb']._get_asset_content(self.stylebundle_xmlid, {})
        return AssetsBundle(self.stylebundle_xmlid, files, env=self.env)

    def _bundle(self, asset, should_create, should_unlink):
        self.counter.clear()
        asset.to_node(debug='assets')
        self.assertEqual(self.counter['create'], int(should_create))
        self.assertEqual(self.counter['unlink'], int(should_unlink))

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
            self.env['ir.attachment'].flush(['checksum'])
            self.cr.execute("update ir_attachment set write_date=clock_timestamp() + interval '10 seconds' where id = (select max(id) from ir_attachment)")

            # Compile a fourth time, without changes
            self._bundle(self._get_asset(), False, False)
