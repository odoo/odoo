import json
from psycopg2.extras import Json
from lxml import etree
from psycopg2 import DataError

from odoo import Command
from odoo.addons.base.models.ir_actions_report import IrActionsReport
from odoo.addons.web_studio.controllers.main import WebStudioController
from odoo.addons.web_studio.controllers.report import WebStudioReportController, get_report_view_copy, _get_and_write_studio_view
from odoo.addons.web.controllers.report import ReportController
from odoo.http import _request_stack, route
from odoo.tests.common import HttpCase, TransactionCase
from odoo.tests import tagged
from odoo.tools import DotDict, mute_logger

parserXML = etree.XMLParser(remove_blank_text=False)
parserHTML = etree.HTMLParser(remove_blank_text=False)
def html_to_xml_tree(stringHTML, body=True):
    temp = etree.fromstring(stringHTML, parser=parserHTML)
    if body:
        temp = temp.getroottree().find("body")[0]
    temp = etree.tostring(temp)
    return etree.fromstring(temp, parser=parserXML)

def _remove_oe_context(tree):
    for node in tree.iter(etree.Element):
        node.attrib.pop("oe-context", None)

def get_combined_and_studio_arch(view):
    studio_view = _get_and_write_studio_view(view)
    return view.get_combined_arch(), studio_view.arch

class TestReportEditor(TransactionCase):

    def setUp(self):
        super(TestReportEditor, self).setUp()
        self.session = DotDict({'debug': ''})
        self.is_frontend = False
        _request_stack.push(self)  # crappy hack to use a fake Request
        self.WebStudioController = WebStudioController()

    def test_copy_inherit_report(self):
        report = self.env['ir.actions.report'].create({
            'name': 'test inherit report user',
            'report_name': 'web_studio.test_inherit_report_user',
            'model': 'res.users',
        })
        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'web_studio.test_inherit_report_hi',
            'key': 'web_studio.test_inherit_report_hi',
            'arch': '''
                <t t-name="web_studio.test_inherit_report_hi">
                    hi
                </t>
            ''',
        })
        parent_view = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'web_studio.test_inherit_report_user_parent',
            'key': 'web_studio.test_inherit_report_user_parent',
            'arch': '''
                <t t-name="web_studio.test_inherit_report_user_parent_view_parent">
                    <t t-call="web_studio.test_inherit_report_hi"/>!
                </t>
            ''',
        })
        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'web_studio.test_inherit_report_user',
            'key': 'web_studio.test_inherit_report_user',
            'arch': '''
                <xpath expr="." position="inside">
                    <t t-call="web_studio.test_inherit_report_hi"/>!!
                </xpath>
            ''',
            'inherit_id': parent_view.id,

        })

        # check original report render to expected output
        report_html = report._render_template(report.report_name).decode()
        self.assertEqual(''.join(report_html.split()), 'hi!hi!!')

        # duplicate original report
        report.copy_report_and_template()
        copy_report = self.env['ir.actions.report'].search([
            ('report_name', '=', 'web_studio.test_inherit_report_user_copy_1'),
        ])

        # check duplicated report render to expected output
        copy_report_html = copy_report._render_template(copy_report.report_name).decode()
        self.assertEqual(''.join(copy_report_html.split()), 'hi!hi!!')

        # check that duplicated view is inheritance combination of original view
        copy_view = self.env['ir.ui.view'].search([
            ('key', '=', copy_report.report_name),
        ])
        self.assertFalse(copy_view.inherit_id, 'copied view does not inherit another one')
        found = len(copy_view.arch_db.split('test_inherit_report_hi_copy_1')) - 1
        self.assertEqual(found, 2, 't-call is duplicated one time and used 2 times')


    def test_duplicate(self):
        # Inheritance during an upgrade work only with loaded views
        # The following force the inheritance to work for all views
        # so the created view is correctly inherited
        self.env = self.env(context={'load_all_views': True})


        # Create a report/view containing "foo"
        report = self.env['ir.actions.report'].create({
            'name': 'test duplicate',
            'report_name': 'web_studio.test_duplicate_foo',
            'model': 'res.users',})

        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'test_duplicate_foo',
            'key': 'web_studio.test_duplicate_foo',
            'arch': "<t t-name='web_studio.test_duplicate_foo'>foo</t>",})

        duplicate_domain = [('report_name', '=like', 'web_studio.test_duplicate_foo_copy_%')]

        # Duplicate the report and retrieve the duplicated view
        report.copy_report_and_template()
        copy1 = self.env['ir.actions.report'].search(duplicate_domain)
        copy1.ensure_one()  # watchdog
        copy1_view = self.env['ir.ui.view'].search([
            ('key', '=', copy1.report_name)])
        copy1_view.ensure_one()  # watchdog

        # Inherit the view to replace "foo" by "bar"
        self.env['ir.ui.view'].create({
            'inherit_id': copy1_view.id,
            'key': copy1.report_name,
            'arch': '''
                <xpath expr="." position="replace">
                    <t t-name='%s'>bar</t>
                </xpath>
            ''' % copy1.report_name,})

        # Assert the duplicated view renders "bar" then unlink the report
        copy1_html = copy1._render_template(copy1.report_name).decode()
        self.assertEqual(''.join(copy1_html.split()), 'bar')
        copy1.unlink()

        # Re-duplicate the original report, it must renders "foo"
        report.copy_report_and_template()
        copy2 = self.env['ir.actions.report'].search(duplicate_domain)
        copy2.ensure_one()
        copy2_html = copy2._render_template(copy2.report_name).decode()
        self.assertEqual(''.join(copy2_html.split()), 'foo')

    def test_copy_custom_model_rendering(self):
        report = self.env['ir.actions.report'].search([('report_name', '=', 'base.report_irmodulereference')])
        report.copy_report_and_template()
        copy = self.env['ir.actions.report'].search([('report_name', '=', 'base.report_irmodulereference_copy_1')])
        report_model = self.env['ir.actions.report']._get_rendering_context_model(copy)
        self.assertIsNotNone(report_model)

    def test_duplicate_keep_translations(self):
        def create_view(name, **kwargs):
            arch = '<div>{}</div>'.format(name)
            if kwargs.get('inherit_id'):
                arch = '<xpath expr="." path="inside">{}</xpath>'.format(arch)
            name = 'web_studio.test_keep_translations_{}'.format(name)
            return self.env['ir.ui.view'].create(dict({
                'type': 'qweb',
                'name': name,
                'key': name,
                'arch': arch,
            }, **kwargs))

        report = self.env['ir.actions.report'].create({
            'name': 'test inherit report user',
            'report_name': 'web_studio.test_keep_translations_ab',
            'model': 'res.users',
        }).with_context(load_all_views=True)

        self.env.ref('base.lang_fr').active = True
        views = report.env['ir.ui.view']
        views += create_view("a_")
        root = views[-1]
        views += create_view("b_")
        views += create_view("aa", inherit_id=root.id, mode="primary")
        views += create_view("ab", inherit_id=root.id)
        target = views[-1]
        views += create_view("aba", inherit_id=target.id)
        views[-1].arch = views[-1].arch.replace('aba', 'a_</div>aba<div>ab')
        views += create_view("abb", inherit_id=target.id, mode="primary")

        for view in views.with_context(lang='fr_FR'):
            terms = view._fields['arch_db'].get_trans_terms(view.arch_db)
            view.update_field_translations('arch_db', {'fr_FR': {term: '%s in fr' % term for term in terms}})

        combined_arch = '<div>a_<div>ab</div><div>a_</div>aba<div>ab</div></div>'
        self.assertEqual(target._read_template(target.id), combined_arch)

        # duplicate original report, views will be combined into one
        report.copy_report_and_template()
        copy_view = self.env['ir.ui.view'].search([
            ('key', '=', 'web_studio.test_keep_translations_ab_copy_1'),
        ])
        self.assertEqual(copy_view.arch, combined_arch)

        # translations of combined views have been copied to the new view
        new_arch = '<div>a_ in fr<div>ab in fr</div><div>a_ in fr</div>aba in fr<div>ab in fr</div></div>'
        self.assertEqual(copy_view.with_context(lang='fr_FR').arch, new_arch)

    def tearDown(self):
        super(TestReportEditor, self).tearDown()
        _request_stack.pop()


@tagged('post_install', '-at_install')
class TestReportEditorUIUnit(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.testAction = cls.env["ir.actions.act_window"].create({
            "name": "simple partner",
            "res_model": "res.partner",
        })
        cls.testActionXmlId = cls.env["ir.model.data"].create({
            "name": "studio_test_partner_action",
            "model": "ir.actions.act_window",
            "module": "web_studio",
            "res_id": cls.testAction.id,
        })
        cls.testMenu = cls.env["ir.ui.menu"].create({
            "name": "Studio Test Partner",
            "action": "ir.actions.act_window,%s" % cls.testAction.id
        })
        cls.testMenuXmlId = cls.env["ir.model.data"].create({
            "name": "studio_test_partner_menu",
            "model": "ir.ui.menu",
            "module": "web_studio",
            "res_id": cls.testMenu.id,
        })


        cls.report = cls.env['ir.actions.report'].create({
            'name': 'test report',
            'report_name': 'web_studio.test_report',
            'model': 'res.partner',
        })
        cls.report_xml_id = cls.env["ir.model.data"].create({
            "name": "studio_test_report",
            "model": "ir.actions.report",
            "module": "web_studio",
            "res_id": cls.report.id,
        })

        cls.main_view = cls.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'web_studio.test_report',
            'key': 'web_studio.test_report',
            'arch': '''
                <t t-name="web_studio.test_report">
                    <t t-call="web.html_container">
                        <div><p><br/></p></div>
                        <t t-foreach="docs" t-as="doc">
                            <t t-call="web_studio.test_report_document" />
                        </t>
                    </t>
                </t>
            ''',
        })
        cls.main_view_xml_id = cls.env["ir.model.data"].create({
            "name": "studio_test_report_view",
            "model": "ir.ui.view",
            "module": "web_studio",
            "res_id": cls.main_view.id,
        })

        cls.main_view_document = cls.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'web_studio.test_report_document',
            'key': 'web_studio.test_report_document',
            'arch': '''
                <t t-name="web_studio.test_report_document">
                    <div><p t-field="doc.name" /></div>
                    <p><br/></p>
                </t>
            ''',
        })
        cls.main_view_document_xml_id = cls.env["ir.model.data"].create({
            "name": "test_report_document",
            "model": "ir.ui.view",
            "module": "web_studio",
            "res_id": cls.main_view_document.id,
        })

    @property
    def tour_url(self):
        return f"/web#action=studio&mode=editor&_action={self.testAction.id}&_tab=reports&_report_id={self.report.id}&menu_id={self.testMenu.id}"

    def _clear_routing(self):
        self.env.registry.clear_cache('routing')

    def test_basic_report_edition(self):
        original_main_view_doc_arch = self.main_view_document.arch
        self.start_tour(self.tour_url, "web_studio.test_basic_report_edition", login="admin")
        self.assertEqual(self.report.name, "modified in test")
        self.assertTrue(self.main_view_xml_id.noupdate)
        self.assertTrue(self.main_view_document_xml_id.noupdate)
        self.assertTrue(self.report_xml_id.noupdate)

        main_arch, studio_arch = get_combined_and_studio_arch(self.main_view)

        self.assertXMLEqual(main_arch, """
            <t t-name="web_studio.test_report">
               <t t-call="web.html_container">
                 <div>
                   <p>edited with odoo editor</p>
                 </div>
                 <t t-foreach="docs" t-as="doc">
                   <t t-call="web_studio.test_report_document"/>
                 </t>
               </t>
             </t>
        """)
        self.assertXMLEqual(studio_arch, """
        <data>
           <xpath expr="/t[@t-name='web_studio.test_report']" position="replace" mode="inner">
             <t t-call="web.html_container">
               <div>
                 <p>edited with odoo editor</p>
               </div>
               <t t-foreach="docs" t-as="doc">
                 <t t-call="web_studio.test_report_document"/>
               </t>
             </t>
           </xpath>
         </data>
        """)

        doc_arch, studio_arch = get_combined_and_studio_arch(self.main_view_document)
         # Not sure about this one. Due to the absence of relevant branding
         # The entire view is replaced (case "entire_view" in report.py)
        self.assertXMLEqual(doc_arch, """
            <t t-name="web_studio.test_report_document">
               <div>
                 <p t-field="doc.name"/>
               </div>
               <p>edited with odoo editor 2</p>
             </t>
        """)
        self.assertXMLEqual(studio_arch, """
        <data>
          <xpath expr="/t[@t-name='web_studio.test_report_document']" position="replace" mode="inner">
            <div>
              <p t-field="doc.name"/>
            </div>
            <p>edited with odoo editor 2</p>
          </xpath>
        </data>
        """)

        copied_view = get_report_view_copy(self.main_view_document)
        self.assertXMLEqual(original_main_view_doc_arch, copied_view.arch)
        self.assertEqual(copied_view.name, "web_studio_backup__web_studio.test_report_document")
        self.assertEqual(copied_view.key, f"web_studio.__backup__._{self.main_view_document.id}_._{self.main_view_document.key}_")
        self.assertFalse(copied_view.active)
        self.assertFalse(copied_view.inherit_id)

    def test_basic_report_edition_without_datas(self):
        passed_in_rendering_context = False

        def _get_rendering_context_mock(self_model, report, docids, data):
            nonlocal passed_in_rendering_context
            passed_in_rendering_context = True
            self.assertTrue(self_model.env.context.get("studio"))
            self.assertTrue(data.get("studio"))
            return {'reason': 'Something went wrong.'}
        self.patch(IrActionsReport, '_get_rendering_context', _get_rendering_context_mock)

        self.start_tour(self.tour_url, "web_studio.test_basic_report_edition", login="admin")
        self.assertTrue(passed_in_rendering_context)

    def test_basic_report_edition_xml(self):
        self.start_tour(self.tour_url, "web_studio.test_basic_report_edition_xml", login="admin")
        self.assertTrue(self.main_view_xml_id.noupdate)
        self.assertTrue(self.main_view_document_xml_id.noupdate)
        self.assertTrue(self.report_xml_id.noupdate)

        self.assertXMLEqual(self.main_view.arch, """
            <t t-name="web_studio.test_report">
              <t t-call="web.html_container">
                <span class="test-added-1">in main view</span>
                <div>
                  <p>
                    <br/>
                  </p>
                </div>
                <t t-foreach="docs" t-as="doc">
                  <t t-call="web_studio.test_report_document"/>
                </t>
              </t>
            </t>
        """)

        self.assertXMLEqual(self.main_view_document.arch, """
            <t t-name="web_studio.test_report_document">
                <div>
                  <p t-field="doc.name"/>
                </div>
                <span class="test-added-0">in document view</span>
                <p>
                    <br/>
                </p>
             </t>
        """)

    def test_basic_report_edition_discard(self):
        self.start_tour(self.tour_url, "web_studio.test_basic_report_edition_discard", login="admin")

        self.assertXMLEqual(self.main_view.arch, """
            <t t-name="web_studio.test_report">
              <t t-call="web.html_container">
                <div><p><br/></p></div>
                <t t-foreach="docs" t-as="doc">
                  <t t-call="web_studio.test_report_document"/>
                </t>
              </t>
            </t>
        """)

        self.assertXMLEqual(self.main_view_document.arch, """
            <t t-name="web_studio.test_report_document">
                <div><p t-field="doc.name"/></div>
                <p><br/></p>
             </t>
        """)

    def test_basic_report_edition_xml_discard(self):
        self.start_tour(self.tour_url, "web_studio.test_basic_report_edition_xml_discard", login="admin")

        self.assertXMLEqual(self.main_view.arch, """
            <t t-name="web_studio.test_report">
              <t t-call="web.html_container">
                <div><p><br/></p></div>
                <t t-foreach="docs" t-as="doc">
                  <t t-call="web_studio.test_report_document"/>
                </t>
              </t>
            </t>
        """)

        self.assertXMLEqual(self.main_view_document.arch, """
            <t t-name="web_studio.test_report_document">
                <div><p t-field="doc.name"/></div>
                <p><br/></p>
             </t>
        """)

    def test_basic_report_edition_error(self):
        save_report = WebStudioReportController.save_report
        self._clear_routing()
        self.addCleanup(self._clear_routing)

        error = None
        @route('/web_studio/save_report', type='json', auth='user')
        def save_report_mocked(*args, **kwargs):
            try:
                return save_report(*args, **kwargs)
            except Exception as e:
                nonlocal error
                error = e
                raise e

        self.patch(WebStudioReportController, "save_report", save_report_mocked)

        main_view_arch = self.main_view.arch
        document_view_arch = self.main_view_document.arch

        with mute_logger("odoo.http"):
            self.start_tour(self.tour_url, "web_studio.test_basic_report_edition_error", login="admin")

        self.assertTrue(error)
        self.assertFalse(self.main_view_xml_id.noupdate)
        self.assertFalse(self.main_view_document_xml_id.noupdate)
        self.assertFalse(self.report_xml_id.noupdate)

        self.assertXMLEqual(self.main_view.arch, main_view_arch)
        self.assertXMLEqual(self.main_view_document.arch, document_view_arch)

    def test_basic_report_edition_xml_error(self):
        save_report = WebStudioReportController.save_report
        self._clear_routing()
        self.addCleanup(self._clear_routing)

        error = None
        @route('/web_studio/save_report', type='json', auth='user')
        def save_report_mocked(*args, **kwargs):
            try:
                return save_report(*args, **kwargs)
            except Exception as e:
                nonlocal error
                error = e
                raise e

        self.patch(WebStudioReportController, "save_report", save_report_mocked)

        main_view_arch = self.main_view.arch
        document_view_arch = self.main_view_document.arch

        with mute_logger("odoo.http"):
            self.start_tour(self.tour_url, "web_studio.test_basic_report_edition_xml_error", login="admin")

        self.assertTrue(error)
        self.assertFalse(self.main_view_xml_id.noupdate)
        self.assertFalse(self.main_view_document_xml_id.noupdate)
        self.assertFalse(self.report_xml_id.noupdate)

        self.assertXMLEqual(self.main_view.arch, main_view_arch)
        self.assertXMLEqual(self.main_view_document.arch, document_view_arch)

    def test_report_reset_archs(self):
        self.main_view_document.arch_fs = "web_studio/tests/test_report_editor.xml"
        self.start_tour(self.tour_url, "web_studio.test_report_reset_archs", login="admin")
        self.assertXMLEqual(self.main_view_document.arch, """<p>from file</p>""")

    def test_report_reset_archs_studio_view(self):
        self.authenticate("admin", "admin")
        studio_view = _get_and_write_studio_view(self.main_view_document, {"arch": "<data/>"})
        self.assertTrue(studio_view.active)
        self.url_open("/web_studio/reset_report_archs",
            data=json.dumps({"params": {"report_id": self.report.id}}),
            headers={"Content-Type": "application/json"}
        )
        self.assertFalse(studio_view.active)

    def test_print_preview(self):
        self.start_tour(self.tour_url, "web_studio.test_print_preview", login="admin")

    def test_table_rendering(self):
        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <p><br/></p>
                <table class="valid_table">
                    <tr><td>I am valid</td></tr>
                </table>

                <table class="invalid_table">
                    <t t-foreach="doc.child_ids" t-as="child">
                        <tr><td>I am not valid</td></tr>
                    </t>
                </table>
            </t>
        """

        self.start_tour(self.tour_url, "web_studio.test_table_rendering", login="admin")
        arch, _ = get_combined_and_studio_arch(self.main_view_document)
        self.assertXMLEqual(arch, """
            <t t-name="web_studio.test_report_document">
               <p>p edited with odooEditor</p>
               <table class="valid_table">
                 <tbody>
                   <tr>
                     <td>I am valid</td>
                   </tr>
                 </tbody>
               </table>
               <table class="invalid_table">
                 <t t-foreach="doc.child_ids" t-as="child">
                   <tr>
                     <td>edited with odooEditor</td>
                   </tr>
                 </t>
               </table>
             </t>
        """)

    def test_nested_table_rendering(self):
        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <table class="invalid_table">
                    <t t-foreach="doc.child_ids" t-as="child">
                        <tr>
                            <td>
                                <t t-set="var" t-value="doc" />
                                <table>
                                    <tr><td>valid</td></tr>
                                </table>
                                <table>
                                    <t t-foreach="doc.child_ids" t-as="subchild">
                                        <tr><td>
                                            <table><tr><td>I am valid</td></tr></table>
                                        </td></tr>
                                    </t>
                                </table>
                            </td>
                        </tr>
                    </t>
                </table>
            </t>
        """
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/web_studio/get_report_qweb",
            data=json.dumps({"params": {"report_id": self.report.id}}),
            headers={"Content-Type": "application/json"}
        )
        qweb_html = response.json()["result"]
        tree = html_to_xml_tree(qweb_html)
        _remove_oe_context(tree)
        div_node = tree.xpath("//t[@t-name='web_studio.test_report_document']")[0][0]
        self.assertXMLEqual(etree.tostring(div_node), """
        <div class="invalid_table" oe-origin-tag="table" oe-origin-style="">
          <t t-foreach="doc.child_ids" t-as="child">
            <div oe-origin-tag="tr" oe-origin-style="">
              <div oe-origin-tag="td" oe-origin-style="">
                <t t-set="var" t-value="doc"/>
                <table>
                  <tr>
                    <td>valid</td>
                  </tr>
                </table>
                <div oe-origin-tag="table" oe-origin-style="">
                  <t t-foreach="doc.child_ids" t-as="subchild">
                    <div oe-origin-tag="tr" oe-origin-style="">
                      <div oe-origin-tag="td" oe-origin-style="">
                        <table><tr><td>I am valid</td></tr></table>
                      </div>
                    </div>
                  </t>
                </div>
              </div>
            </div>
          </t>
        </div>
        """)

    def test_field_placeholder(self):
        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <div><p t-field="doc.name" title="Name"/></div>
                <p><br/></p>
            </t>
        """

        url = self.tour_url.replace("/web", "/web?debug=assets")
        self.start_tour(url, "web_studio.test_field_placeholder", login="admin")

        arch, _ = get_combined_and_studio_arch(self.main_view)
        self.assertXMLEqual(arch, """
            <t t-name="web_studio.test_report">
               <t t-call="web.html_container">
                 <div>
                   <p><br/>edited with odooEditor</p>
                 </div>
                 <t t-foreach="docs" t-as="doc">
                   <t t-call="web_studio.test_report_document"/>
                 </t>
               </t>
             </t>
        """)

        arch, _ = get_combined_and_studio_arch(self.main_view_document)
        self.assertXMLEqual(arch, """
            <t t-name="web_studio.test_report_document">
               <div>
                 <p t-field="doc.name" title="Name"/>
               </div>
               <p>
                 <span t-field="doc.function">some default value</span>
                 <br/>
               </p>
             </t>
        """)

    def test_toolbar_appearance(self):
        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <div><p t-field="doc.name" title="Name"/></div>
                <p><br/></p>
            </t>
        """

        self.start_tour(self.tour_url, "web_studio.test_toolbar_appearance", login="admin")

    def test_add_field_blank_report(self):
        studio_views = self.env["ir.ui.view"].search([("key", "=ilike", "studio_customization.%")])
        self.start_tour(self.tour_url, "web_studio.test_add_field_blank_report", login="admin")
        new_view = self.env["ir.ui.view"].search([("key", "=ilike", "studio_customization.%"), ("id", "not in", studio_views.ids), ("name", "like", "document")])

        new_view_arch, _ = get_combined_and_studio_arch(new_view)
        self.assertXMLEqual(new_view_arch, """
            <t t-name="studio_report_document">
                <div class="page">
                    <div class="oe_structure"><span t-field="doc.function">some default value</span>Custo</div>
                </div>
            </t>
        """)

    def test_edition_without_lang(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.env["res.users"].browse(2).lang = "fr_FR"
        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <p>original term</p>
            </t>
        """

        translations = {
            "fr_FR": {
                "original term": "translated term"
            }
        }
        self.main_view_document.update_field_translations("arch_db", translations)
        self.start_tour(self.tour_url, "web_studio.test_edition_without_lang", login="admin")

        _, studio_arch = get_combined_and_studio_arch(self.main_view_document)

        self.assertXMLEqual(studio_arch, """
           <data><xpath expr="/t[@t-name='web_studio.test_report_document']" position="replace" mode="inner">
              <p>original term edited</p>
            </xpath></data>
        """)

        new_translations = self.main_view_document.get_field_translations("arch_db")
        new_translations_values = {k["lang"]: k for k in new_translations[0]}
        self.assertEqual(
            new_translations_values["en_US"]["source"],
            "original term"
        )
        self.assertEqual(
            new_translations_values["en_US"]["value"],
            ""
        )
        self.assertEqual(
            new_translations_values["fr_FR"]["source"],
            "original term"
        )
        self.assertEqual(
            new_translations_values["fr_FR"]["value"],
            "translated term"
        )
        studio_translation = _get_and_write_studio_view(self.main_view_document).get_field_translations("arch_db")
        studio_translation_values = {k["lang"]: k for k in studio_translation[0]}
        self.assertEqual(
            studio_translation_values["en_US"]["source"],
            "original term edited"
        )
        self.assertEqual(
            studio_translation_values["en_US"]["value"],
            ""
        )
        self.assertEqual(
            studio_translation_values["fr_FR"]["source"],
            "original term edited"
        )
        self.assertEqual(
            studio_translation_values["fr_FR"]["value"],
            "translated edited term"
        )

    def test_report_xml_other_record(self):
        ResPartner = self.env["res.partner"]
        p1 = ResPartner.create({'name': "partner_1"})
        p2 = ResPartner.create({'name': "partner_2"})

        original_search = ResPartner.search

        def mock_search(self, *args, **kwargs):
            if not args and not kwargs:
                return (p1 | p2).ids
            return original_search(*args, **kwargs)

        self.patch(type(ResPartner), "search", mock_search)

        self.start_tour(self.tour_url, "web_studio.test_report_xml_other_record", login="admin")

    def test_partial_eval(self):
        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <t t-set="my_children" t-value="doc.child_ids" />
                <t t-set="some_var" t-value="'some_value'" />
                <t t-foreach="my_children" t-as="child">
                    <div t-att-class="'lol' if report_type != 'html' else 'notlol'">lol</div>
                    <div t-attf-class="{{ 'couic' }}" >couic</div>
                </t>
            </t>
        """
        self.start_tour(self.tour_url, "web_studio.test_partial_eval", login="admin")

    def test_render_multicompany(self):
        company1 = self.env.company

        self.main_view_document.arch = """
            <t t-call="web.external_layout">
                <div>doc</div>
            </t>
        """
        external_report_layout_id = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'web_studio.test_layout',
            'key': 'web_studio.test_layout',
            'arch': '''
                <t t-name="web_studio.test_report">
                    <div class="test_layout">
                        <img t-if="company.logo" t-att-src="image_data_uri(company.logo)" style="max-height: 45px;" alt="Logo"/>
                        <div><t t-out="0" /></div>
                    </div>
                </t>
            ''',
        })
        company2 = self.env["res.company"].create({"name": "couic", "external_report_layout_id": external_report_layout_id.id})
        self.env["res.users"].browse(2).write({"company_ids": [Command.link(company2.id)]})

        tour_url = self.tour_url + f"&cids={company2.id}-{company1.id}"
        self.start_tour(tour_url, "web_studio.test_render_multicompany", login="admin")

    def test_report_edition_binary_field(self):
        self.env["ir.model.fields"].create({
            "field_description": "New File",
            "name": "x_new_file",
            "ttype": "binary",
            "model": "res.company",
            "model_id": self.env["ir.model"]._get('res.company').id,
            "state": "manual",
        })
        self.env["ir.model.fields"].create({
            "field_description": "New File filename",
            "name": "x_new_file_filename",
            "ttype": "char",
            "model": "res.partner",
            "model_id": self.env["ir.model"]._get('res.company').id,
            "state": "manual",
        })
        self.env["ir.model.fields"].create({
            "field_description": "New Image",
            "name": "x_new_image",
            "ttype": "binary",
            "model": "res.company",
            "model_id": self.env["ir.model"]._get('res.company').id,
            "state": "manual",
        })

        self.start_tour(self.tour_url, "web_studio.test_report_edition_binary_field", login="admin")

        arch, _ = get_combined_and_studio_arch(self.main_view_document)
        self.assertXMLEqual(arch, """
            <t t-name="web_studio.test_report_document">
                <div><p t-field="doc.name"/></div>
                <p><span t-field="doc.company_id.x_new_file">file default value</span><span t-field="doc.company_id.x_new_image" t-options-widget="\'image\'" t-options-qweb_img_raw_data="1">image default value</span><br/></p>
            </t>
        """)

    def test_report_edition_dynamic_table(self):
        url = self.tour_url.replace("/web", "/web?debug=assets")
        self.start_tour(url, "web_studio.test_report_edition_dynamic_table", login="admin")

        arch, _ = get_combined_and_studio_arch(self.main_view_document)
        self.assertXMLEqual(arch, """
            <t t-name="web_studio.test_report_document">
                <div>
                    <p t-field="doc.name"/>
                </div>
                <table class="table table-sm">
                    <tbody>
                        <tr class="border-bottom border-top-0 border-start-0 border-end-0 border-2 border-dark fw-bold">
                            <td>First Column</td>
                        </tr>
                        <tr t-foreach="doc.activity_ids" t-as="x2many_record">
                           <td>
                               <span t-field="x2many_record.summary">Some Summary</span>
                             <br/>
                           </td>
                        </tr>
                    </tbody>
                  </table>
                  <p>
                    <br/>
                  </p>
            </t>
        """)

    def test_saving_xml_editor_reload(self):
        self.start_tour(self.tour_url, "web_studio.test_saving_xml_editor_reload", login="admin")

    def test_error_at_loading(self):
        bad_view = self.env["ir.ui.view"].create({
            "name": "bad view",
            "inherit_id": self.main_view_document.id,
            "arch": """<data />"""
        })
        arch = """<data>
                    <xpath expr="/form/h1" position="after">
                        will crash
                    </xpath>
                </data>"""
        self.env.cr.execute(
            """UPDATE ir_ui_view SET arch_db = %s WHERE id = %s""",
            (Json({"en_US": arch}), bad_view.id)
        )

        with mute_logger("odoo.http"):
            self.start_tour(self.tour_url, "web_studio.test_error_at_loading", login="admin")

        with mute_logger("odoo.http"):
            url = self.tour_url.replace("/web", "/web?debug=1")
            self.start_tour(url, "web_studio.test_error_at_loading_debug", login="admin")

    def test_xml_and_form_diff(self):
        url = self.tour_url.replace("/web", "/web?debug=1")
        self.start_tour(url, "web_studio.test_xml_and_form_diff", login="admin")

    def test_record_model_differs_from_action(self):
        dummy = self.env["ir.model"].create({
            "name": "dummy.test",
            "model": "x_dummy.test"
        })
        self.env['ir.model.access'].create({
            "name": "dummy",
            "perm_read": True,
            "model_id": dummy.id,
        })

        self.report.model = dummy.model
        self.report.name = "dummy test"
        self.start_tour(f"/web#action=studio&mode=editor&_action={self.testAction.id}&_tab=reports&menu_id={self.testMenu.id}", "web_studio.test_record_model_differs_from_action", login="admin")

    def test_recursive_t_calls(self):
        self.authenticate("admin", "admin")
        self.main_view_document.arch = """
             <t t-name="web_studio.test_report_document">
                <div><p t-field="doc.name" /></div>
                <p><br/></p>
                <t t-call="web_studio.test_report_document"><div /></t>
            </t>
        """

        response = self.url_open(
            "/web_studio/get_report_qweb",
            data=json.dumps({"params": {"report_id": self.report.id}}),
            headers={"Content-Type": "application/json"}
        )

        qweb_html = response.json()["result"]
        tree = html_to_xml_tree(qweb_html)
        _remove_oe_context(tree)
        tcall = tree.xpath("//t[@t-call='web_studio.test_report_document']")[0]
        self.assertXMLEqual(etree.tostring(tcall), f"""
           <t t-call="web_studio.test_report_document" ws-call-key="2" ws-view-id="{self.main_view.id}">
             <t t-name="web_studio.test_report_document" ws-view-id="{self.main_view_document.id}">
               <div>
                 <p t-field="doc.name" oe-expression-readable="Name"/>
               </div>
               <p>
                 <br/>
               </p>
               <t t-call="web_studio.test_report_document" ws-call-key="1" ws-view-id="{self.main_view_document.id}">
                    <div/>
               </t>
             </t>
           </t>
        """)

    def test_can_have_multiple_times_same_t_call(self):
        self.authenticate("admin", "admin")
        self.main_view.arch = """
            <t t-name="web_studio.test_report">
                <t t-call="web.html_container">
                    <div>
                    <t t-call="web_studio.test_report_document">
                        <h1/>
                    </t>
                    <t t-call="web_studio.test_report_document">
                        <h2/>
                    </t>
                    </div>
                </t>
            </t>
        """
        self.main_view_document.arch = """<t t-name="web_studio.test_report_document"><t t-out="0" /></t> """
        response = self.url_open(
            "/web_studio/get_report_qweb",
            data=json.dumps({"params": {"report_id": self.report.id}}),
            headers={"Content-Type": "application/json"}
        )
        qweb_html = response.json()["result"]
        tree = html_to_xml_tree(qweb_html)
        _remove_oe_context(tree)
        tcall = tree.xpath("//t[@t-call='web_studio.test_report_document']")
        self.assertEqual(len(tcall), 2)

        self.assertXMLEqual(etree.tostring(tcall[0]), f"""
         <t t-call="web_studio.test_report_document" ws-call-key="2" ws-view-id="{self.main_view.id}">
           <t t-name="web_studio.test_report_document" ws-view-id="{self.main_view_document.id}">
             <t oe-origin-t-out="0">
                <t ws-view-id="{self.main_view.id}" ws-call-group-key="1" ws-call-key="2" ws-real-children="1">
                  <h1/>
                </t>
             </t>
           </t>
         </t>
        """)
        self.assertXMLEqual(etree.tostring(tcall[1]), f"""
        <t t-call="web_studio.test_report_document" ws-call-key="3" ws-view-id="{self.main_view.id}">
           <t t-name="web_studio.test_report_document" ws-view-id="{self.main_view_document.id}">
             <t oe-origin-t-out="0">
               <t ws-view-id="{self.main_view.id}" ws-call-group-key="1" ws-call-key="3" ws-real-children="1">
                 <h2/>
               </t>
             </t>
           </t>
         </t>
        """)

    def test_remove_branding_on_copy(self):
        self.start_tour(self.tour_url, "web_studio.test_remove_branding_on_copy", login="admin")

    def test_test_different_view_document_name(self):
        self.main_view_document_xml_id.name = "test_report_document_1"
        self.start_tour(self.tour_url, "web_studio.test_different_view_document_name", login="admin")

    def test_formalize_qweb_client_t_call_structure(self):
        self.authenticate("admin", "admin")
        html_container = self.env["ir.ui.view"]._get("web.html_container")

        tcalled_0 = self.env["ir.ui.view"].create({
            'type': 'qweb',
            'name': 'web_studio.t_call_0',
            'key': 'web_studio.t_call_0',
            'arch': """<t t-name="web_studio.t_call_0">
                    <div class="call_0"><t t-out="0" /></div>
                </t>"""
        })

        tcalled_1 = self.env["ir.ui.view"].create({
            'type': 'qweb',
            'name': 'web_studio.t_call_1',
            'key': 'web_studio.t_call_1',
            'arch': """<t t-name="web_studio.t_call_1">
                <div class="call_1"><p> call one </p><t t-out="0" /></div>
            </t>"""
        })

        self.main_view_document.arch = """
                <t t-name="web_studio.test_report_document">
                    <div>
                        <t t-call="web_studio.t_call_0">
                            <div>
                                <p> call zero one </p>
                                <t t-call="web_studio.t_call_1">
                                    <p> call zero two </p>
                                </t>
                            </div>
                        </t>
                    </div>
                </t>
            """
        response = self.url_open(
            "/web_studio/get_report_qweb",
            data=json.dumps({"params": {"report_id": self.report.id}}),
            headers={"Content-Type": "application/json"}
        )
        qweb_html = response.json()["result"]
        tree = html_to_xml_tree(qweb_html)
        _remove_oe_context(tree)

        verification_tree = etree.fromstring(
        """<div id="wrapwrap" oe-context="{&quot;docs&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: false}, &quot;company&quot;: {&quot;model&quot;: &quot;res.company&quot;, &quot;name&quot;: &quot;Companies&quot;, &quot;in_foreach&quot;: false}}">
           <main>
             <t ws-was-t-out="1">
               <t ws-view-id="{html_container.id}" ws-call-group-key="1" ws-call-key="1" ws-real-children="1">
                 <t ws-was-t-out="1">
                   <t ws-view-id="{main_view.id}" ws-call-group-key="1" ws-call-key="1" ws-real-children="1">
                     <div>
                       <p>
                         <br/>
                       </p>
                     </div>
                     <t t-foreach="docs" t-as="doc" oe-context="{&quot;docs&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: false}, &quot;company&quot;: {&quot;model&quot;: &quot;res.company&quot;, &quot;name&quot;: &quot;Companies&quot;, &quot;in_foreach&quot;: false}, &quot;doc&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: true}}">
                       <t t-call="web_studio.test_report_document" ws-call-key="2" ws-view-id="{main_view.id}">
                         <t t-name="web_studio.test_report_document" ws-view-id="{main_view_document.id}" oe-context="{&quot;docs&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: false}, &quot;company&quot;: {&quot;model&quot;: &quot;res.company&quot;, &quot;name&quot;: &quot;Companies&quot;, &quot;in_foreach&quot;: false}, &quot;doc&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: true}}">
                           <div>
                             <t t-call="web_studio.t_call_0" ws-call-key="1" ws-view-id="{main_view_document.id}">
                               <t t-name="web_studio.t_call_0" ws-view-id="{tcalled_0.id}" oe-context="{&quot;docs&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: false}, &quot;company&quot;: {&quot;model&quot;: &quot;res.company&quot;, &quot;name&quot;: &quot;Companies&quot;, &quot;in_foreach&quot;: false}, &quot;doc&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: true}}">
                                 <div class="call_0">
                                   <t ws-was-t-out="1">
                                     <t ws-view-id="{main_view_document.id}" ws-call-group-key="1" ws-call-key="1" ws-real-children="1">
                                       <div>
                                         <p> call zero one </p>
                                         <t t-call="web_studio.t_call_1" ws-call-key="2" ws-view-id="{main_view_document.id}">
                                           <t t-name="web_studio.t_call_1" ws-view-id="{tcalled_1.id}" oe-context="{&quot;docs&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: false}, &quot;company&quot;: {&quot;model&quot;: &quot;res.company&quot;, &quot;name&quot;: &quot;Companies&quot;, &quot;in_foreach&quot;: false}, &quot;doc&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: true}}">
                                             <div class="call_1">
                                               <p> call one </p>
                                               <t ws-was-t-out="1">
                                                 <t ws-view-id="{main_view_document.id}" ws-call-group-key="1" ws-call-key="2" ws-real-children="1">
                                                   <p> call zero two </p>
                                                 </t>
                                               </t>
                                             </div>
                                           </t>
                                         </t>
                                       </div>
                                     </t>
                                   </t>
                                 </div>
                               </t>
                             </t>
                           </div>
                         </t>
                       </t>
                     </t>
                   </t>
                 </t>
               </t>
             </t>
           </main>
         </div>""")
        _remove_oe_context(verification_tree)

        self.assertXMLEqual(
            etree.tostring(tree),
            etree.tounicode(tree).format(
                main_view=self.main_view, main_view_document=self.main_view_document, tcalled_0=tcalled_0, tcalled_1=tcalled_1, html_container=html_container
            )
        )

    def test_edit_main_arch(self):
        self.env["ir.ui.view"].create({
            'type': 'qweb',
            'name': 'web_studio.t_call_0',
            'key': 'web_studio.t_call_0',
            'arch': """<t t-name="web_studio.t_call_0">
                    <div class="call_0"><t t-out="0" /></div>
                </t>"""
        })

        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <div class="outside-t-call">outside</div>
                <t t-call="web_studio.t_call_0">
                    <t t-set="somevar" t-value="'someValue'" />
                    <div class="in-t-call">inside</div>
                </t>
            </t>
        """

        self.start_tour(self.tour_url, "web_studio.test_edit_main_arch", login="admin")

        arch, studio_arch = get_combined_and_studio_arch(self.main_view_document)
        self.assertXMLEqual(arch, """
         <t t-name="web_studio.test_report_document">
           <div class="added"/>
           <div class="outside-t-call">outside</div>
           <t t-call="web_studio.t_call_0">
             <t t-set="somevar" t-value="'someValue'"/>
             <div class="in-t-call">inside</div>
           </t>
         </t>
        """)
        self.assertXMLEqual(studio_arch, """
        <data>
           <xpath expr="/t[@t-name='web_studio.test_report_document']" position="replace" mode="inner">
             <div class="added"/>
             <div class="outside-t-call">outside</div>
             <t t-call="web_studio.t_call_0">
               <t t-set="somevar" t-value="'someValue'"/>
               <div class="in-t-call">inside</div>
             </t>
           </xpath>
         </data>
        """)

    def test_edit_in_t_call(self):
        self.env["ir.ui.view"].create({
            'type': 'qweb',
            'name': 'web_studio.t_call_0',
            'key': 'web_studio.t_call_0',
            'arch': """<t t-name="web_studio.t_call_0">
                    <div class="call_0"><t t-out="0" /></div>
                </t>"""
        })

        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <div class="outside-t-call">outside</div>
                <t t-call="web_studio.t_call_0">
                    <t t-set="somevar" t-value="'someValue'" />
                    <div class="in-t-call">inside</div>
                </t>
            </t>
        """

        self.start_tour(self.tour_url, "web_studio.test_edit_in_t_call", login="admin")

        arch, studio_arch = get_combined_and_studio_arch(self.main_view_document)
        self.assertXMLEqual(arch, """
         <t t-name="web_studio.test_report_document">
           <div class="outside-t-call">outside</div>
           <t t-call="web_studio.t_call_0">
             <t t-set="somevar" t-value="'someValue'"/>
             <div class="added"/>
             <div class="in-t-call">inside</div>
           </t>
         </t>
        """)
        self.assertXMLEqual(studio_arch, """
        <data>
           <xpath expr="/t[@t-name='web_studio.test_report_document']" position="replace" mode="inner">
             <div class="outside-t-call">outside</div>
             <t t-call="web_studio.t_call_0">
               <t t-set="somevar" t-value="'someValue'"/>
               <div class="added"/>
               <div class="in-t-call">inside</div>
             </t>
           </xpath>
         </data>
        """)

    def test_edit_main_and_in_t_call(self):
        self.env["ir.ui.view"].create({
            'type': 'qweb',
            'name': 'web_studio.t_call_0',
            'key': 'web_studio.t_call_0',
            'arch': """<t t-name="web_studio.t_call_0">
                    <div class="call_0"><t t-out="0" /></div>
                </t>"""
        })

        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <div class="outside-t-call">outside</div>
                <t t-call="web_studio.t_call_0">
                    <t t-set="somevar" t-value="'someValue'" />
                    <div class="in-t-call">inside</div>
                </t>
            </t>
        """

        self.start_tour(self.tour_url, "web_studio.test_edit_main_and_in_t_call", login="admin")

        arch, studio_arch = get_combined_and_studio_arch(self.main_view_document)
        self.assertXMLEqual(arch, """
         <t t-name="web_studio.test_report_document">
           <div class="added0"/>
           <div class="outside-t-call">outside</div>
           <t t-call="web_studio.t_call_0">
             <t t-set="somevar" t-value="'someValue'"/>
             <div class="added1"/>
             <div class="in-t-call">inside</div>
           </t>
         </t>
        """)
        self.assertXMLEqual(studio_arch, """
        <data>
           <xpath expr="/t[@t-name='web_studio.test_report_document']" position="replace" mode="inner">
             <div class="added0"/>
             <div class="outside-t-call">outside</div>
             <t t-call="web_studio.t_call_0">
               <t t-set="somevar" t-value="'someValue'"/>
               <div class="added1"/>
               <div class="in-t-call">inside</div>
             </t>
           </xpath>
         </data>
        """)

    def test_image_crop(self):
        attach = self.env["ir.attachment"].create({
            "name": "test image crop",
            "datas": "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVR4nGJxKFrEwMDAxAAGgAAAAP//D+IBWx9K7TUAAAAASUVORK5CYII="
        })
        self.main_view_document.arch = f"""
            <t t-name="test_main_doc">
                <img class="myimg"
                    data-original-id="{attach.id}"
                    data-original-src="/web/image/{attach.id}"
                    src="data:image/png;base64,{attach.datas.decode("utf-8")}"/>
            </t>
        """

        self.start_tour(self.tour_url, "web_studio.test_image_crop", login="admin")

    def test_add_non_searchable_field(self):
        with self.with_user("admin"):
            partner = self.env["res.partner"].search([], limit=1)
        partner.image_1024 = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVR4nGJxKFrEwMDAxAAGgAAAAP//D+IBWx9K7TUAAAAASUVORK5CYII="
        self.start_tour(self.tour_url, "web_studio.test_add_non_searchable_field", login="admin")
        arch, _ = get_combined_and_studio_arch(self.main_view_document)
        self.assertXMLEqual(arch, """
            <t t-name="web_studio.test_report_document">
                <div><p t-field="doc.name"/></div>
                <p>
                    <span
                        t-field="doc.avatar_1024"
                        t-options-widget="'image'"
                        t-options-qweb_img_raw_data="1"
                    >file default value</span>
                    <br/>
                </p>
            </t>
        """)

    def test_translations_are_copied(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.main_view_document.arch = """
            <t t-name="web_studio.test_report_document">
                <div>term1</div>
            </t>
        """
        self.main_view_document.update_field_translations("arch_db", {"fr_FR": {"term1": "baguette"}})

        inheriting = self.env["ir.ui.view"].create({
            "type": "qweb",
            "inherit_id": self.main_view_document.id,
            "arch": """<data>
                <xpath expr="//div[1]" position="after">
                    <div>term2</div>
                </xpath>
            </data>"""
        })
        inheriting.update_field_translations("arch_db", {"fr_FR": {"term2": "croissant"}})

        self.start_tour(self.tour_url, "web_studio.test_translations_are_copied", login="admin")

        html, _ = self.report.with_context(lang="fr_FR")._render_qweb_html(self.report.id, [1])
        main = etree.fromstring(html).find(".//main")
        self.assertXMLEqual(etree.tostring(main), """
        <main>
            <div>
                <p><br/></p>
            </div>
            <div>baguette</div>
            <div>term3 from edition</div>
            <div>croissant</div>
        </main>
        """)

    def test_evaluate_bad_queries(self):
        self.main_view_document.arch = """
        <t t-name="web_studio.test_report_document">
            <div>
                <div t-attf-class="{{ docs.search([('create_date', '&lt;', 'false')]) }}">term1</div>
                <div t-attf-class="{{ docs.search([('create_date', '&lt;', 'false')]) }}">term2</div>
                <div t-attf-class="res_partner_{{ bool(docs.search([('create_date', '!=', False)], limit=1)) }}">term3</div>
            </div>
        </t>"""

        ResPartner = self.env.registry.get("res.partner")
        search = ResPartner.search
        errors = []

        def mock_search(record_set, *args, **kwargs):
            try:
                return search(record_set, *args, **kwargs)
            except Exception as e:
                errors.append(e)
                raise

        self.patch(ResPartner, "search", mock_search)

        self.authenticate("admin", "admin")
        with mute_logger("odoo.sql_db"):
            response = self.url_open(
                "/web_studio/get_report_qweb",
                data=json.dumps({"params": {"report_id": self.report.id}}),
                headers={"Content-Type": "application/json"}
            )
        self.assertEqual(len(errors), 2)
        for e in errors:
            self.assertTrue(isinstance(e, DataError))

        qweb_html = response.json()["result"]
        tree = html_to_xml_tree(qweb_html)
        _remove_oe_context(tree)
        div_node = tree.xpath("//t[@t-name='web_studio.test_report_document']")[0][0]
        self.assertXMLEqual(etree.tostring(div_node), """
        <div>
            <div t-attf-class="{{ docs.search([('create_date', '&lt;', 'false')]) }}" oe-origin-class="" class="">term1</div>
            <div t-attf-class="{{ docs.search([('create_date', '&lt;', 'false')]) }}" oe-origin-class="" class="">term2</div>
            <div t-attf-class="res_partner_{{ bool(docs.search([('create_date', '!=', False)], limit=1)) }}" oe-origin-class="" class="res_partner_True">term3</div>
        </div>
        """)
