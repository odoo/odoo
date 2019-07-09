# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
import datetime
import errno
import os
import time
from unittest.mock import patch

from odoo import api
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.modules.module import get_resource_path
from odoo.tests import HttpCase
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
        self.env['res.lang'].load_lang('ar_SY')


    def _get_asset(self, xmlid, env=None):
        env = (env or self.env)
        files, remains = env['ir.qweb']._get_asset_content(xmlid, env.context)
        return AssetsBundle(xmlid, files, env=env)

    def _any_ira_for_bundle(self, type, lang=None):
        """ Returns all ir.attachments associated to a bundle, regardless of the verion.
        """
        user_direction = self.env['res.lang'].search([('code', '=', (lang or self.env.user.lang))]).direction
        bundle = self.jsbundle_xmlid if type == 'js' else self.cssbundle_xmlid
        return self.env['ir.attachment'].search([
            ('url', '=like', '/web/content/%-%/{0}{1}%.{2}'.format(('rtl/' if type == 'css' and user_direction == 'rtl' else ''), bundle, type))
        ])

    def test_01_generation(self):
        """ Checks that a bundle creates an ir.attachment record when its `js` method is called
        for the first time.
        """
        self.bundle = self._get_asset(self.jsbundle_xmlid, env=self.env)

        # there shouldn't be any attachment associated to this bundle
        self.assertEquals(len(self._any_ira_for_bundle('js')), 0)
        self.assertEquals(len(self.bundle.get_attachments('js')), 0)

        # trigger the first generation and, thus, the first save in database
        self.bundle.js()

        # there should be one attachment associated to this bundle
        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)
        self.assertEquals(len(self.bundle.get_attachments('js')), 1)

    def test_02_access(self):
        """ Checks that the bundle's cache is working, i.e. that the bundle creates only one
        ir.attachment record when rendered multiple times.
        """
        bundle0 = self._get_asset(self.jsbundle_xmlid)
        bundle0.js()

        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

        version0 = bundle0.version
        ira0 = self._any_ira_for_bundle('js')
        date0 = ira0.create_date

        bundle1 = self._get_asset(self.jsbundle_xmlid)
        bundle1.js()

        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

        version1 = bundle1.version
        ira1 = self._any_ira_for_bundle('js')
        date1 = ira1.create_date

        self.assertEquals(version0, version1)
        self.assertEquals(date0, date1)

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
            self.assertNotEquals(last_modified0, last_modified1)
            self.assertNotEquals(version0, version1)

            # check if the previous attachment is correctly cleaned
            self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

    def test_04_content_invalidation(self):
        """ Checks that a bundle is invalidated when its content is modified by adding a file to
        source.
        """
        bundle0 = self._get_asset(self.jsbundle_xmlid)
        bundle0.js()
        files0 = bundle0.files
        version0 = bundle0.version

        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

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

        self.assertNotEquals(files0, files1)
        self.assertNotEquals(version0, version1)

        # check if the previous attachment are correctly cleaned
        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

    def test_05_debug(self):
        """ Checks that a bundle rendered in debug mode outputs non-minified assets.
        """
        debug_bundle = self._get_asset(self.jsbundle_xmlid)
        content = debug_bundle.to_html(debug='assets')
        # find back one of the original asset file
        self.assertIn('/test_assetsbundle/static/src/js/test_jsfile1.js', content)

        # there shouldn't be any assets created in debug mode
        self.assertEquals(len(self._any_ira_for_bundle('js')), 0)

    def test_06_paginated_css_generation1(self):
        """ Checks that a bundle creates enough ir.attachment records when its `css` method is called
        for the first time while the number of css rules exceed the limit.
        """
        # note: changing the max_css_rules of a bundle does not invalidate its attachments
        # self.cssbundle_xlmid contains 3 rules
        self.bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))
        self.bundle.css()
        self.assertEquals(len(self._any_ira_for_bundle('css')), 3)
        self.assertEquals(len(self.bundle.get_attachments('css')), 3)

    def test_07_paginated_css_generation2(self):
        # self.cssbundle_xlmid contains 3 rules
        self.bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 2}))
        self.bundle.css()
        self.assertEquals(len(self._any_ira_for_bundle('css')), 2)
        self.assertEquals(len(self.bundle.get_attachments('css')), 2)

    def test_08_paginated_css_generation3(self):
        # self.cssbundle_xlmid contains 3 rules
        self.bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 3}))
        self.bundle.css()
        self.assertEquals(len(self._any_ira_for_bundle('css')), 1)
        self.assertEquals(len(self.bundle.get_attachments('css')), 1)

    def test_09_paginated_css_access(self):
        """ Checks that the bundle's cache is working, i.e. that a bundle creates only enough
        ir.attachment records when rendered multiple times.
        """
        bundle0 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))
        bundle0.css()

        self.assertEquals(len(self._any_ira_for_bundle('css')), 3)

        version0 = bundle0.version
        ira0, ira1, ira2 = self._any_ira_for_bundle('css')
        date0 = ira0.create_date
        date1 = ira1.create_date
        date2 = ira2.create_date

        bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))
        bundle1.css()

        self.assertEquals(len(self._any_ira_for_bundle('css')), 3)

        version1 = bundle1.version
        ira3, ira4, ira5 = self._any_ira_for_bundle('css')
        date3 = ira1.create_date
        date4 = ira1.create_date
        date5 = ira1.create_date

        self.assertEquals(version0, version1)
        self.assertEquals(date0, date3)
        self.assertEquals(date1, date4)
        self.assertEquals(date2, date5)

    def test_10_paginated_css_date_invalidation(self):
        """ Checks that a bundle is invalidated when one of its assets' modification date is changed.
        """
        bundle0 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))
        bundle0.css()
        last_modified0 = bundle0.last_modified
        version0 = bundle0.version

        path = get_resource_path('test_assetsbundle', 'static', 'src', 'css', 'test_cssfile1.css')
        bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))

        with self._touch(path):
            bundle1.css()
            last_modified1 = bundle1.last_modified
            version1 = bundle1.version

            self.assertNotEquals(last_modified0, last_modified1)
            self.assertNotEquals(version0, version1)

            # check if the previous attachment is correctly cleaned
            self.assertEquals(len(self._any_ira_for_bundle('css')), 3)

    def test_11_paginated_css_content_invalidation(self):
        """ Checks that a bundle is invalidated when its content is modified by adding a file to
        source.
        """
        bundle0 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))
        bundle0.css()
        files0 = bundle0.files
        version0 = bundle0.version

        self.assertEquals(len(self._any_ira_for_bundle('css')), 3)

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

        bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'check_view_ids': view.ids, 'max_css_rules': 1}))
        bundle1.css()
        files1 = bundle1.files
        version1 = bundle1.version

        self.assertNotEquals(files0, files1)
        self.assertNotEquals(version0, version1)

        # check if the previous attachment are correctly cleaned
        self.assertEquals(len(self._any_ira_for_bundle('css')), 4)

    def test_12_paginated_css_debug(self):
        """ Check that a bundle in debug mode outputs non-minified assets.
        """
        debug_bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))
        content = debug_bundle.to_html(debug='assets')
        # find back one of the original asset file
        self.assertIn('/test_assetsbundle/static/src/css/test_cssfile1.css', content)

        # there shouldn't be any assets created in debug mode
        self.assertEquals(len(self._any_ira_for_bundle('css')), 0)

    def test_13_paginated_css_order(self):
        # self.cssbundle_xlmid contains 3 rules
        self.bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))
        stylesheets = self.bundle.css()

        self.assertTrue(stylesheets[0].url.endswith('.0.css'))
        self.assertTrue(stylesheets[1].url.endswith('.1.css'))
        self.assertTrue(stylesheets[2].url.endswith('.2.css'))

    def test_14_duplicated_css_assets(self):
        """ Checks that if the bundle's ir.attachment record is duplicated, the bundle is only sourced once. This could
        happen if multiple transactions try to render the bundle simultaneously.
        """
        bundle0 = self._get_asset(self.cssbundle_xmlid)
        bundle0.css()
        self.assertEquals(len(self._any_ira_for_bundle('css')), 1)

        # duplicate the asset bundle
        ira0 = self._any_ira_for_bundle('css')
        ira1 = ira0.copy()
        self.assertEquals(len(self._any_ira_for_bundle('css')), 2)
        self.assertEquals(ira0.store_fname, ira1.store_fname)

        # the ir.attachment records should be deduplicated in the bundle's content
        content = bundle0.to_html()
        self.assertEqual(content.count('test_assetsbundle.bundle2.0.css'), 1)

    # Language direction specific tests

    def test_15_rtl_css_generation(self):
        """ Checks that a bundle creates an ir.attachment record when its `css` method is called
        for the first time for language with different direction and separate bundle is created for rtl direction.
        """
        self.bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))

        # there shouldn't be any attachment associated to this bundle
        self.assertEquals(len(self._any_ira_for_bundle('css', lang='ar_SY')), 0)
        self.assertEquals(len(self.bundle.get_attachments('css')), 0)

        # trigger the first generation and, thus, the first save in database
        self.bundle.css()

        # there should be one attachment associated to this bundle
        self.assertEquals(len(self._any_ira_for_bundle('css', lang='ar_SY')), 1)
        self.assertEquals(len(self.bundle.get_attachments('css')), 1)

    def test_16_ltr_and_rtl_css_access(self):
        """ Checks that the bundle's cache is working, i.e. that the bundle creates only one
        ir.attachment record when rendered multiple times for rtl direction also check we have two css bundles,
        one for ltr and one for rtl.
        """
        # Assets access for en_US language
        ltr_bundle0 = self._get_asset(self.cssbundle_xmlid)
        ltr_bundle0.css()

        self.assertEquals(len(self._any_ira_for_bundle('css')), 1)

        ltr_version0 = ltr_bundle0.version
        ltr_ira0 = self._any_ira_for_bundle('css')
        ltr_date0 = ltr_ira0.create_date

        ltr_bundle1 = self._get_asset(self.cssbundle_xmlid)
        ltr_bundle1.css()

        self.assertEquals(len(self._any_ira_for_bundle('css')), 1)

        ltr_version1 = ltr_bundle1.version
        ltr_ira1 = self._any_ira_for_bundle('css')
        ltr_date1 = ltr_ira1.create_date

        self.assertEquals(ltr_version0, ltr_version1)
        self.assertEquals(ltr_date0, ltr_date1)

        # Assets access for ar_SY language
        rtl_bundle0 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle0.css()

        self.assertEquals(len(self._any_ira_for_bundle('css', lang='ar_SY')), 1)

        rtl_version0 = rtl_bundle0.version
        rtl_ira0 = self._any_ira_for_bundle('css', lang='ar_SY')
        rtl_date0 = rtl_ira0.create_date

        rtl_bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))
        rtl_bundle1.css()

        self.assertEquals(len(self._any_ira_for_bundle('css', lang='ar_SY')), 1)

        rtl_version1 = rtl_bundle1.version
        rtl_ira1 = self._any_ira_for_bundle('css', lang='ar_SY')
        rtl_date1 = rtl_ira1.create_date

        self.assertEquals(rtl_version0, rtl_version1)
        self.assertEquals(rtl_date0, rtl_date1)

        # Checks rtl and ltr bundles are different
        self.assertNotEquals(ltr_ira1.id, rtl_ira1.id)

        # Check two bundles are available, one for ltr and one for rtl
        css_bundles = self.env['ir.attachment'].search([
            ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(self.cssbundle_xmlid, 'css'))
        ])
        self.assertEquals(len(css_bundles), 2)

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
            self.assertNotEquals(ltr_last_modified0, ltr_last_modified1)
            self.assertNotEquals(ltr_version0, ltr_version1)

            rtl_bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))

            rtl_bundle1.css()
            rtl_last_modified1 = rtl_bundle1.last_modified
            rtl_version1 = rtl_bundle1.version
            rtl_ira1 = self._any_ira_for_bundle('css', lang='ar_SY')
            self.assertNotEquals(rtl_last_modified0, rtl_last_modified1)
            self.assertNotEquals(rtl_version0, rtl_version1)

            # Checks rtl and ltr bundles are different
            self.assertNotEquals(ltr_ira1.id, rtl_ira1.id)

            # check if the previous attachment is correctly cleaned
            css_bundles = self.env['ir.attachment'].search([
                ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(self.cssbundle_xmlid, 'css'))
            ])
            self.assertEquals(len(css_bundles), 2)

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
        self.assertEquals(len(css_bundles), 2)

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

        self.assertNotEquals(ltr_files0, ltr_files1)
        self.assertNotEquals(ltr_version0, ltr_version1)

        rtl_bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'check_view_ids': view.ids, 'lang': 'ar_SY'}))
        rtl_bundle1.css()
        rtl_files1 = rtl_bundle1.files
        rtl_version1 = rtl_bundle1.version
        rtl_ira1 = self._any_ira_for_bundle('css', lang='ar_SY')

        self.assertNotEquals(rtl_files0, rtl_files1)
        self.assertNotEquals(rtl_version0, rtl_version1)

        # Checks rtl and ltr bundles are different
        self.assertNotEquals(ltr_ira1.id, rtl_ira1.id)

        # check if the previous attachment are correctly cleaned
        css_bundles = self.env['ir.attachment'].search([
            ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(self.cssbundle_xmlid, 'css'))
        ])
        self.assertEquals(len(css_bundles), 2)

    def test_19_css_in_debug_assets(self):
        """ Checks that a bundle rendered in debug mode(assets) with right to left language direction stores css files in assets bundle.
        """
        debug_bundle = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'lang': 'ar_SY'}))
        content = debug_bundle.to_html(debug='assets')

        # css file should be available in assets bundle as user's lang direction is rtl
        self.assertIn('/test_assetsbundle/static/src/css/test_cssfile1/rtl/{0}.css'.format(self.cssbundle_xmlid), content)

        # there should be assets(css) created in debug mode as user's lang direction is rtl
        css_bundle = self.env['ir.attachment'].search([
            ('url', '=', '/test_assetsbundle/static/src/css/test_cssfile1/rtl/{0}.css'.format(self.cssbundle_xmlid))
        ])
        self.assertEquals(len(css_bundle), 1)

    def test_20_exteral_lib_assets(self):
        html = self.env['ir.ui.view'].render_template('test_assetsbundle.template2')
        attachments = self.env['ir.attachment'].search([('url', '=like', '/web/content/%-%/test_assetsbundle.bundle4.%')])
        self.assertEquals(len(attachments), 2)
        self.assertEqual(html.strip(), ("""<!DOCTYPE html>
<html>
    <head>
        <link rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="%(css)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="%(js)s"></script>
    </head>
    <body>
    </body>
</html>""" % {"js": attachments[0].url, "css": attachments[1].url}).encode('utf8'))

    def test_21_exteral_lib_assets_debug_mode(self):
        html = self.env['ir.ui.view'].render_template('test_assetsbundle.template2', {"debug": "assets"})
        attachments = self.env['ir.attachment'].search([('url', '=like', '/web/content/%-%/test_assetsbundle.bundle4.%')])
        self.assertEquals(len(attachments), 0)
        self.assertEqual(html.strip(), ("""<!DOCTYPE html>
<html>
    <head>
        <link rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="/test_assetsbundle/static/src/css/test_cssfile1.css"/>
        <link type="text/css" rel="stylesheet" href="/test_assetsbundle/static/src/css/test_cssfile2.css"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="/test_assetsbundle/static/src/js/test_jsfile1.js"></script>
        <script type="text/javascript" src="/test_assetsbundle/static/src/js/test_jsfile2.js"></script>
        <script type="text/javascript" src="/test_assetsbundle/static/src/js/test_jsfile3.js"></script>
    </head>
    <body>
    </body>
</html>""").encode('utf8'))


class TestAssetsBundleInBrowser(HttpCase):
    def test_01_js_interpretation(self):
        """ Checks that the javascript of a bundle is correctly interpreted.
        """
        self.phantom_js(
            "/test_assetsbundle/js",
            "a + b + c === 6 ? console.log('ok') : console.log('error')",
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

        self.phantom_js(
            "/test_assetsbundle/js",
            "a + b + c + d === 10 ? console.log('ok') : console.log('error')",
            login="admin",
        )


class TestAssetsBundleWithIRAMock(FileTouchable):
    def setUp(self):
        super(TestAssetsBundleWithIRAMock, self).setUp()
        self.stylebundle_xmlid = 'test_assetsbundle.bundle3'
        self.counter = counter = Counter()

        # patch methods 'create' and 'unlink' of model 'ir.attachment'
        @api.model
        def create(self, vals):
            counter.update(['create'])
            return create.origin(self, vals)

        @api.multi
        def unlink(self):
            counter.update(['unlink'])
            return unlink.origin(self)

        self.env['ir.attachment']._patch_method('create', create)
        self.addCleanup(self.env['ir.attachment']._revert_method, 'create')

        self.env['ir.attachment']._patch_method('unlink', unlink)
        self.addCleanup(self.env['ir.attachment']._revert_method, 'unlink')

    def _get_asset(self):
        files, remains = self.env['ir.qweb']._get_asset_content(self.stylebundle_xmlid, {})
        return AssetsBundle(self.stylebundle_xmlid, files, remains, env=self.env)

    def _bundle(self, asset, should_create, should_unlink):
        self.counter.clear()
        asset.to_html(debug='assets')
        self.assertEquals(self.counter['create'], int(should_create))
        self.assertEquals(self.counter['unlink'], int(should_unlink))

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
            self.cr.execute("update ir_attachment set write_date=clock_timestamp() + interval '10 seconds' where id = (select max(id) from ir_attachment)")

            # Compile a fourth time, without changes
            self._bundle(self._get_asset(), False, False)
