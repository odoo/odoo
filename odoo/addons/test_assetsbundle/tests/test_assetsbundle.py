# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
from os import utime
import time

from odoo import api
from odoo.addons.base.ir.ir_qweb import AssetsBundle
from odoo.modules.module import get_resource_path
from odoo.tests import HttpCase
from odoo.tests.common import TransactionCase


class TestJavascriptAssetsBundle(TransactionCase):
    def setUp(self):
        super(TestJavascriptAssetsBundle, self).setUp()
        self.jsbundle_xmlid = 'test_assetsbundle.bundle1'
        self.cssbundle_xmlid = 'test_assetsbundle.bundle2'

    def _get_asset(self, xmlid, env=None):
        env = (env or self.env)
        files, remains = env['ir.qweb']._get_asset_content(xmlid, env.context)
        return AssetsBundle(xmlid, files, remains, env=env)

    def _any_ira_for_bundle(self, type):
        """ Returns all ir.attachments associated to a bundle, regardless of the verion.
        """
        bundle = self.jsbundle_xmlid if type == 'js' else self.cssbundle_xmlid
        return self.env['ir.attachment'].search([
            ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(bundle, type))
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
        utime(path, None)  # touch

        bundle1 = self._get_asset(self.jsbundle_xmlid)
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
        remains0 = bundle0.remains
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
        remains1 = bundle1.remains
        version1 = bundle1.version

        self.assertNotEquals(files0, files1)
        self.assertEquals(remains0, remains1)
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
        utime(path, None)  # touch

        bundle1 = self._get_asset(self.cssbundle_xmlid, env=self.env(context={'max_css_rules': 1}))
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
        remains0 = bundle0.remains
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
        remains1 = bundle1.remains
        version1 = bundle1.version

        self.assertNotEquals(files0, files1)
        self.assertEquals(remains0, remains1)
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
        with self.registry.cursor() as test_cursor:
            view_arch = """
            <data>
                <xpath expr="." position="inside">
                    <script type="text/javascript">
                        var d = 4;
                    </script>
                </xpath>
            </data>
            """
            self.env(cr=test_cursor)['ir.ui.view'].create({
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


class TestAssetsBundleWithIRAMock(TransactionCase):
    def setUp(self):
        super(TestAssetsBundleWithIRAMock, self).setUp()
        self.lessbundle_xmlid = 'test_assetsbundle.bundle3'
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

    def _bundle(self, should_create, should_unlink):
        self.counter.clear()
        files, remains = self.env['ir.qweb']._get_asset_content(self.lessbundle_xmlid, {})
        asset = AssetsBundle(self.lessbundle_xmlid, files, remains, env=self.env)
        asset.to_html(debug='assets')
        self.assertEquals(self.counter['create'], int(should_create))
        self.assertEquals(self.counter['unlink'], int(should_unlink))

    def test_01_debug_mode_assets(self):
        """ Checks that the ir.attachments records created for compiled less assets in debug mode
        are correctly invalidated.
        """
        # Compile for the first time
        self._bundle(True, False)

        # Compile a second time, without changes
        self._bundle(False, False)

        # Touch the file and compile a third time
        path = get_resource_path('test_assetsbundle', 'static', 'src', 'less', 'test_lessfile1.less')
        t = time.time() + 5
        utime(path, (t, t))   # touch
        self._bundle(True, True)

        # Because we are in the same transaction since the beginning of the test, the first asset
        # created and the second one have the same write_date, but the file's last modified date
        # has really been modified. If we do not update the write_date to a posterior date, we are
        # not able to reproduce the case where we compile this bundle again without changing
        # anything.
        self.cr.execute("update ir_attachment set write_date=clock_timestamp() + interval '10 seconds' where id = (select max(id) from ir_attachment)")

        # Compile a fourth time, without changes
        self._bundle(False, False)
