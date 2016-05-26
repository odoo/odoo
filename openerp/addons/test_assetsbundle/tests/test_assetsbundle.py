# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import HttpCase
from openerp.tests.common import TransactionCase
from openerp.addons.base.ir.ir_qweb import AssetsBundle
from openerp.modules.module import get_resource_path

from mock import patch
from os import utime
import time


class TestJavascriptAssetsBundle(TransactionCase):
    def setUp(self):
        super(TestJavascriptAssetsBundle, self).setUp()
        self.jsbundle_xmlid = 'test_assetsbundle.bundle1'
        self.cssbundle_xmlid = 'test_assetsbundle.bundle2'

    def _any_ira_for_bundle(self, type):
        """ Returns all ir.attachments associated to a bundle, regardless of the verion.
        """
        bundle = self.jsbundle_xmlid if type == 'js' else self.cssbundle_xmlid
        return self.registry['ir.attachment'].search(self.cr, self.uid,[
            ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(bundle, type))
        ])

    def test_01_generation(self):
        """ Checks that a bundle creates an ir.attachment record when its `js` method is called
        for the first time.
        """
        self.bundle = AssetsBundle(self.jsbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry)

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
        bundle0 = AssetsBundle(self.jsbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry)
        bundle0.js()

        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

        version0 = bundle0.version
        ira0 = self.registry['ir.attachment'].browse(self.cr, self.uid, self._any_ira_for_bundle('js')[0])
        date0 = ira0.create_date

        bundle1 = AssetsBundle(self.jsbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry)
        bundle1.js()

        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

        version1 = bundle1.version
        ira1 = self.registry['ir.attachment'].browse(self.cr, self.uid, self._any_ira_for_bundle('js')[0])
        date1 = ira1.create_date

        self.assertEquals(version0, version1)
        self.assertEquals(date0, date1)

    def test_03_date_invalidation(self):
        """ Checks that a bundle is invalidated when one of its assets' modification date is changed.
        """
        bundle0 = AssetsBundle(self.jsbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry)
        bundle0.js()
        last_modified0 = bundle0.last_modified
        version0 = bundle0.version

        path = get_resource_path('test_assetsbundle', 'static', 'src', 'js', 'test_jsfile1.js')
        utime(path, None)  # touch

        bundle1 = AssetsBundle(self.jsbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry)
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
        bundle0 = AssetsBundle(self.jsbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry)
        bundle0.js()
        html0 = bundle0.html
        version0 = bundle0.version

        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

        view_arch = """
        <data>
            <xpath expr="." position="inside">
                <script type="text/javascript" src="/test_assetsbundle/static/src/js/test_jsfile4.js"/>
            </xpath>
        </data>
        """
        bundle_id = self.browse_ref(self.jsbundle_xmlid).id
        newid = self.registry['ir.ui.view'].create(self.cr, self.uid, {
            'name': 'test bundle inheritance',
            'type': 'qweb',
            'arch': view_arch,
            'inherit_id': bundle_id,
        })

        bundle1 = AssetsBundle(self.jsbundle_xmlid, cr=self.cr, uid=self.uid, context={'check_view_ids': [newid]}, registry=self.registry)
        bundle1.js()
        html1 = bundle1.html
        version1 = bundle1.version

        self.assertNotEquals(html0, html1)
        self.assertNotEquals(version0, version1)

        # check if the previous attachment are correctly cleaned
        self.assertEquals(len(self._any_ira_for_bundle('js')), 1)

    def test_05_debug(self):
        """ Checks that a bundle rendered in debug mode outputs non-minified assets.
        """
        debug_bundle = AssetsBundle(self.jsbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry)
        content = debug_bundle.to_html(debug=True)
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
        self.bundle = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=1)
        self.bundle.css()
        self.assertEquals(len(self._any_ira_for_bundle('css')), 3)
        self.assertEquals(len(self.bundle.get_attachments('css')), 3)

    def test_07_paginated_css_generation2(self):
        # self.cssbundle_xlmid contains 3 rules
        self.bundle = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=2)
        self.bundle.css()
        self.assertEquals(len(self._any_ira_for_bundle('css')), 2)
        self.assertEquals(len(self.bundle.get_attachments('css')), 2)

    def test_08_paginated_css_generation3(self):
        # self.cssbundle_xlmid contains 3 rules
        self.bundle = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=3)
        self.bundle.css()
        self.assertEquals(len(self._any_ira_for_bundle('css')), 1)
        self.assertEquals(len(self.bundle.get_attachments('css')), 1)

    def test_09_paginated_css_access(self):
        """ Checks that the bundle's cache is working, i.e. that a bundle creates only enough
        ir.attachment records when rendered multiple times.
        """
        bundle0 = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=1)
        bundle0.css()

        self.assertEquals(len(self._any_ira_for_bundle('css')), 3)

        version0 = bundle0.version
        ira0 = self.registry['ir.attachment'].browse(self.cr, self.uid, self._any_ira_for_bundle('css')[0])
        date0 = ira0.create_date
        ira1 = self.registry['ir.attachment'].browse(self.cr, self.uid, self._any_ira_for_bundle('css')[1])
        date1 = ira1.create_date
        ira2 = self.registry['ir.attachment'].browse(self.cr, self.uid, self._any_ira_for_bundle('css')[2])
        date2 = ira2.create_date

        bundle1 = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=1)
        bundle1.css()

        self.assertEquals(len(self._any_ira_for_bundle('css')), 3)

        version1 = bundle1.version
        ira3 = self.registry['ir.attachment'].browse(self.cr, self.uid, self._any_ira_for_bundle('css')[0])
        date3 = ira1.create_date
        ira4 = self.registry['ir.attachment'].browse(self.cr, self.uid, self._any_ira_for_bundle('css')[1])
        date4 = ira1.create_date
        ira5 = self.registry['ir.attachment'].browse(self.cr, self.uid, self._any_ira_for_bundle('css')[2])
        date5 = ira1.create_date

        self.assertEquals(version0, version1)
        self.assertEquals(date0, date3)
        self.assertEquals(date1, date4)
        self.assertEquals(date2, date5)

    def test_10_paginated_css_date_invalidation(self):
        """ Checks that a bundle is invalidated when one of its assets' modification date is changed.
        """
        bundle0 = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=1)
        bundle0.css()
        last_modified0 = bundle0.last_modified
        version0 = bundle0.version

        path = get_resource_path('test_assetsbundle', 'static', 'src', 'css', 'test_cssfile1.css')
        utime(path, None)  # touch

        bundle1 = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=1)
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
        bundle0 = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=1)
        bundle0.css()
        html0 = bundle0.html
        version0 = bundle0.version

        self.assertEquals(len(self._any_ira_for_bundle('css')), 3)

        view_arch = """
        <data>
            <xpath expr="." position="inside">
                <link rel="stylesheet" href="/test_assetsbundle/static/src/css/test_cssfile2.css"/>
            </xpath>
        </data>
        """
        bundle_id = self.browse_ref(self.cssbundle_xmlid).id
        newid = self.registry['ir.ui.view'].create(self.cr, self.uid, {
            'name': 'test bundle inheritance',
            'type': 'qweb',
            'arch': view_arch,
            'inherit_id': bundle_id,
        })

        bundle1 = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={'check_view_ids': [newid]}, registry=self.registry, max_css_rules=1)
        bundle1.css()
        html1 = bundle1.html
        version1 = bundle1.version

        self.assertNotEquals(html0, html1)
        self.assertNotEquals(version0, version1)

        # check if the previous attachment are correctly cleaned
        self.assertEquals(len(self._any_ira_for_bundle('css')), 4)

    def test_12_paginated_css_debug(self):
        """ Check that a bundle in debug mode outputs non-minified assets.
        """
        debug_bundle = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=1)
        content = debug_bundle.to_html(debug=True)
        # find back one of the original asset file
        self.assertIn('/test_assetsbundle/static/src/css/test_cssfile1.css', content)

        # there shouldn't be any assets created in debug mode
        self.assertEquals(len(self._any_ira_for_bundle('css')), 0)

    def test_13_paginated_css_order(self):
        # self.cssbundle_xlmid contains 3 rules
        self.bundle = AssetsBundle(self.cssbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry, max_css_rules=1)
        stylesheets = self.bundle.css()

        self.assertTrue(stylesheets[0].url.endswith('.0.css'))
        self.assertTrue(stylesheets[1].url.endswith('.1.css'))
        self.assertTrue(stylesheets[2].url.endswith('.2.css'))


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
            self.registry['ir.ui.view'].create(test_cursor, self.uid, {
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
        self.patcher1 = patch('openerp.addons.base.ir.ir_attachment.ir_attachment.create', wraps=self.registry['ir.attachment'].create)
        self.patcher2 = patch('openerp.addons.base.ir.ir_attachment.ir_attachment.unlink', wraps=self.registry['ir.attachment'].unlink)
        self.mock_ira_create = self.patcher1.start()
        self.mock_ira_unlink = self.patcher2.start()

    def _bundle(self, should_create, should_unlink):
        self.mock_ira_create.reset_mock()
        self.mock_ira_unlink.reset_mock()
        AssetsBundle(self.lessbundle_xmlid, cr=self.cr, uid=self.uid, context={}, registry=self.registry).to_html(debug=True)
        self.assertEquals(self.mock_ira_create.call_count, int(should_create))
        self.assertEquals(self.mock_ira_unlink.call_count, int(should_unlink))

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

    def tearDown(self):
        self.patcher2.stop()
        self.patcher1.stop()
        super(TestAssetsBundleWithIRAMock, self).tearDown()
