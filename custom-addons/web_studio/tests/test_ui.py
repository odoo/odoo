# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

import logging

from lxml import etree
from lxml.builder import E
import json

import odoo.tests
from odoo import Command, api, http
from odoo.tools import mute_logger
from odoo.addons.web_studio.controllers.main import WebStudioController

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_new_app_and_report(self):
        if not odoo.tests.loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.start_tour("/web", 'web_studio_new_app_tour', login="admin")

        # the report tour is based on the result of the former tour
        self.start_tour("/web?debug=tests", 'web_studio_new_report_tour', login="admin")
        self.start_tour("/web?debug=tests", "web_studio_new_report_basic_layout_tour", login="admin")

    def test_optional_fields(self):
        self.start_tour("/web?debug=tests", 'web_studio_hide_fields_tour', login="admin")

    def test_model_option_value(self):
        self.start_tour("/web?debug=tests", 'web_studio_model_option_value_tour', login="admin")

    def test_rename(self):
        self.start_tour("/web?debug=tests", 'web_studio_main_and_rename', login="admin", timeout=200)

    def test_approval(self):
        self.start_tour("/web?debug=tests", 'web_studio_approval_tour', login="admin")

    def test_background(self):
        attachment = self.env['ir.attachment'].create({
            'datas': b'R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=',
            'name': 'testFilename.gif',
            'public': True,
            'mimetype': 'image/gif'
        })
        self.env.company.background_image = attachment.datas
        self.start_tour("/web?debug=tests", 'web_studio_custom_background_tour', login="admin")

    def test_create_app_with_pipeline_and_user_assignment(self):
        self.start_tour("/web?debug=tests", 'web_studio_create_app_with_pipeline_and_user_assignment', login="admin")

    def test_alter_field_existing_in_multiple_views(self):
        created_model_name = None
        studio_model_create = type(self.env["ir.model"]).studio_model_create
        def mock_studio_model_create(*args, **kwargs):
            nonlocal created_model_name
            res = studio_model_create(*args, **kwargs)
            created_model_name = res[0].model
            return res

        self.patch(type(self.env["ir.model"]), "studio_model_create", mock_studio_model_create)
        self.start_tour("/web?debug=tests", 'web_studio_alter_field_existing_in_multiple_views_tour', login="admin")

        # we can't assert xml equality as a lot of stuff in the arch are set randomly
        view = self.env["ir.ui.view"].search([("model", "=", created_model_name), ("type", "=", "form")], limit=1)
        tree = etree.fromstring(view.get_combined_arch())
        root = tree.getroottree()

        fields_of_interest = tree.xpath("//field[@name='message_partner_ids']")
        self.assertEqual(len(fields_of_interest), 2)

        # First field is on the main model: not below another field
        # The second one is in a subview
        self.assertEqual(root.getpath(fields_of_interest[0]), "/form/sheet/group/group[1]/field")
        self.assertEqual(root.getpath(fields_of_interest[1]), "/form/sheet/field[2]/tree/field[1]")

        # The tour in its final steps is putting invisible on the field in the subview
        self.assertEqual(fields_of_interest[0].get("invisible"), None)
        self.assertEqual(fields_of_interest[1].get("invisible"), None)

        self.assertEqual(fields_of_interest[0].get("column_invisible"), None)
        self.assertEqual(fields_of_interest[1].get("column_invisible"), "True")

    def test_add_field_into_empty_group_by(self):
        self.start_tour("/web?debug=tests", 'web_studio_add_field_into_empty_group_by', login="admin")

def _get_studio_view(view):
    domain = [('inherit_id', '=', view.id), ('name', '=', "Odoo Studio: %s customization" % (view.name))]
    return view.search(domain, order='priority desc, name desc, id desc', limit=1)

def _transform_arch_for_assert(arch_string):
    parser = etree.XMLParser(remove_blank_text=True)
    arch_string = etree.fromstring(arch_string, parser=parser)
    return etree.tostring(arch_string, pretty_print=True, encoding='unicode')

def assertViewArchEqual(test, original, expected):
    if original:
        original = _transform_arch_for_assert(original)
    if expected:
        expected = _transform_arch_for_assert(expected)
    test.assertEqual(original, expected)

def watch_edit_view(test, on_edit_view):
    def clear_routing():
        test.env.registry.clear_cache('routing')

    clear_routing()
    edit_view = WebStudioController.edit_view

    @http.route('/web_studio/edit_view', type='json', auth='user')
    def edit_view_mocked(*args, **kwargs):
        on_edit_view(*args, **kwargs)
        return edit_view(*args, **kwargs)

    test.patch(WebStudioController, "edit_view", edit_view_mocked)
    test.addCleanup(clear_routing)

def watch_create_new_field(test, on_create_new_field):
    create_new_field = WebStudioController.create_new_field

    def create_new_field_mocked(*args, **kwargs):
        response = create_new_field(*args, **kwargs)
        on_create_new_field(*args, **kwargs)
        return response

    test.patch(WebStudioController, "create_new_field", create_new_field_mocked)

def setup_view_editor_data(cls):
    cls.env.company.country_id = cls.env.ref('base.us')
    cls.testView = cls.env["ir.ui.view"].create({
        "name": "simple partner",
        "model": "res.partner",
        "type": "form",
        "arch": '''
            <form>
                <field name="name" />
            </form>
        '''
    })
    cls.testAction = cls.env["ir.actions.act_window"].create({
        "name": "simple partner",
        "res_model": "res.partner",
        "view_ids": [Command.create({"view_id": cls.testView.id, "view_mode": "form"})]
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


@odoo.tests.tagged('post_install', '-at_install')
class TestStudioUIUnit(odoo.tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        setup_view_editor_data(cls)

    def create_empty_app(self):
        self.newModel = self.env['ir.model'].create({
            'name': 'Test Model',
            'model': 'x_test_model',
            'field_id': [
                (0, 0, {'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
            ]
        })
        self.newModel._setup_access_rights()

        self.newView = self.env["ir.ui.view"].create({
            "name": "simpleView",
            "model": "x_test_model",
            "type": "form",
            "arch": '''
                <form>
                    <group>
                        <field name="x_name" />
                    </group>
                </form>
            '''
        })

        self.newAction = self.env["ir.actions.act_window"].create({
            "name": "simple model",
            "res_model": "x_test_model",
            "view_ids": [Command.create({"view_id": self.newView.id, "view_mode": "form"})]
        })

        self.newActionXmlId = self.env["ir.model.data"].create({
            "name": "studio_app_action",
            "model": "ir.actions.act_window",
            "module": "web_studio",
            "res_id": self.newAction.id,
        })

        self.newMenu = self.env["ir.ui.menu"].create({
            "name": "StudioApp",
            "action": "ir.actions.act_window,%s" % self.newAction.id
        })

        self.newMenuXmlId = self.env["ir.model.data"].create({
            "name": "studio_app_menu",
            "model": "ir.ui.menu",
            "module": "web_studio",
            "res_id": self.newMenu.id,
        })

    @mute_logger('odoo.http')
    def test_web_studio_check_method_in_model(self):
        self.start_tour("/web?debug=tests", 'web_studio_check_method_in_model', login="admin")

    def test_create_action_button_in_form_view(self):
        self.start_tour("/web?debug=tests", 'web_studio_test_create_action_button_in_form_view', login="admin")
        studioView = _get_studio_view(self.testView)
        model = self.env["ir.model"].search([("model", "=", "res.partner")])
        action1 = self.env["ir.actions.actions"].search([
            ("name", "=", "Privacy Lookup"),
            ("type", "=", "ir.actions.server"),
            ("binding_model_id", "=", model.id),
        ])
        action1 = self.env[action1.type].browse(action1.id)
        assertViewArchEqual(self, studioView.arch, """
            <data>
                <xpath expr="//form[1]/field[@name='name']" position="before">
                    <header>
                        <button string="web_studio_new_button_action_name" name="{action1_Id}" type="action"/>
                    </header>
                </xpath>
            </data>""".format(action1_Id=action1.xml_id))
        self.start_tour("/web?debug=tests", 'web_studio_test_create_second_action_button_in_form_view', login="admin")
        action2 = self.env["ir.actions.actions"].search([
            ("name", "=", "Download (vCard)"),
            ("type", "=", "ir.actions.server"),
            ("binding_model_id", "=", model.id),
        ])
        action2 = self.env[action2.type].browse(action2.id)

        assertViewArchEqual(self, studioView.arch, """
            <data>
                <xpath expr="//form[1]/field[@name='name']" position="before">
                    <header>
                        <button string="web_studio_new_button_action_name" name="{action1_Id}" type="action"/>
                        <button string="web_studio_other_button_action_name" name="{action2_Id}" type="action"/>
                    </header>
                </xpath>
            </data>""".format(action1_Id=action1.xml_id, action2_Id=action2.xml_id))
        self.start_tour("/web?debug=tests", 'web_studio_test_remove_action_button_in_form_view', login="admin")
        self.start_tour("/web?debug=tests", 'web_studio_test_remove_action_button_in_form_view', login="admin")
        arch = """<data>
                <xpath expr="//form[1]/field[@name='name']" position="before">
                    <header>
                        </header>
                </xpath>
            </data>"""
        #FIXME Can't do it otherwise cause of indentation problems
        self.assertEqual(studioView.arch.replace(" ", ""), arch.replace(" ", ""))

    def test_create_action_button_in_list_view(self):
        self.start_tour("/web?debug=tests", 'web_studio_test_create_action_button_in_list_view', login="admin")
        view = self.env["ir.ui.view"].search([
            ("name", "=", "res.partner.tree"),
        ], limit=1)
        studioView = _get_studio_view(view)
        model = self.env["ir.model"].search([("model", "=", "res.partner")])
        action = self.env["ir.actions.actions"].search([
            ("name", "=", "Privacy Lookup"),
            ("type", "=", "ir.actions.server"),
            ("binding_model_id", "=", model.id),
        ])
        action = self.env[action.type].browse(action.id)
        assertViewArchEqual(self, studioView.arch, """
            <data>
                <xpath expr="//field[@name='display_name']" position="before">
                    <header>
                        <button string="web_studio_new_button_action_name" name="{actionId}" type="action"/>
                    </header>
                </xpath>
            </data>""".format(actionId=action.xml_id))
        self.start_tour("/web?debug=tests", 'web_studio_test_remove_action_button_in_list_view', login="admin")
        arch = """<data>
                <xpath expr="//field[@name='display_name']" position="before">
                    <header>
                    </header>
                </xpath>
            </data>"""
        #FIXME Can't do it otherwise cause of indentation problems
        self.assertEqual(studioView.arch.replace(" ", ""), arch.replace(" ", ""))

    def test_form_view_not_altered_by_studio_xml_edition(self):
        self.start_tour("/web?debug=tests", 'web_studio_test_form_view_not_altered_by_studio_xml_edition', login="admin", timeout=200)

    def test_edit_with_xml_editor(self):
        studioView = self.env["ir.ui.view"].create({
            'type': self.testView.type,
            'model': self.testView.model,
            'inherit_id': self.testView.id,
            'mode': 'extension',
            'priority': 99,
            'arch': "<data><xpath expr=\"//field[@name='name']\" position=\"after\"> <div class=\"someDiv\"/></xpath></data>",
            'name': "Odoo Studio: %s customization" % (self.testView.name)
        })

        self.start_tour("/web?debug=tests", 'web_studio_test_edit_with_xml_editor', login="admin", timeout=200)
        self.assertEqual(studioView.arch, "<data/>")

    def test_enter_x2many_edition_and_add_field(self):
        doesNotHaveGroup = self.env["res.groups"].create({
            "name": "studio does not have"
        })
        doesNotHaveGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_doesnothavegroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": doesNotHaveGroup.id,
        })

        userView = self.env["ir.ui.view"].create({
            "name": "simple user",
            "model": "res.users",
            "type": "form",
            "arch": '''
                <form class="test-user-form">
                    <t groups="{doesnothavegroup}" >
                        <div class="condition_group" />
                    </t>
                    <group>
                        <field name="name" />
                    </group>
                </form>
            '''.format(doesnothavegroup=doesNotHaveGroupXmlId.complete_name)
        })

        userViewXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_user_view",
            "model": "ir.ui.view",
            "module": "web_studio",
            "res_id": userView.id,
        })

        self.testView.arch = '''<form><field name="user_ids" context="{'form_view_ref': '%s'}" /></form>''' % userViewXmlId.complete_name
        studioView = _get_studio_view(self.testView)
        self.assertFalse(studioView.exists())

        self.start_tour("/web?debug=tests", 'web_studio_enter_x2many_edition_and_add_field', login="admin", timeout=200)
        studioView = _get_studio_view(self.testView)

        assertViewArchEqual(self, studioView.arch, """
            <data>
               <xpath expr="//field[@name='user_ids']" position="inside">
                 <form class="test-user-form">
                   <t groups="{doesnothavegroup}" >
                     <div class="condition_group" />
                   </t>
                   <group>
                     <field name="name"/>
                     <field name="log_ids"/>
                   </group>
                 </form>
               </xpath>
             </data>
            """.format(doesnothavegroup=doesNotHaveGroupXmlId.complete_name))

    def test_enter_x2many_auto_inlined_subview(self):
        userView = self.env["ir.ui.view"].create({
            "name": "simple user",
            "model": "res.users",
            "type": "tree",
            "arch": '''
                <tree class="test-user-list">
                    <field name="display_name" />
                </tree>
            '''
        })

        userViewXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_user_view",
            "model": "ir.ui.view",
            "module": "web_studio",
            "res_id": userView.id,
        })

        self.testView.arch = '''<form><field name="user_ids" context="{'tree_view_ref': '%s'}" /></form>''' % userViewXmlId.complete_name
        studioView = _get_studio_view(self.testView)
        self.assertFalse(studioView.exists())

        self.start_tour("/web?debug=tests", 'web_studio_enter_x2many_auto_inlined_subview', login="admin", timeout=200)
        studioView = _get_studio_view(self.testView)

        assertViewArchEqual(self, studioView.arch, """
            <data>
               <xpath expr="//field[@name='user_ids']" position="inside">
                 <tree class="test-user-list">
                   <field name="display_name" />
                   <field name="log_ids" optional="show" />
                 </tree>
               </xpath>
             </data>
            """)

    def test_enter_x2many_auto_inlined_subview_with_multiple_field_matching(self):
        user_view = self.env["ir.ui.view"].create({
            "name": "simple user",
            "model": "res.users",
            "type": "tree",
            "arch": '''
                <tree class="test-user-list">
                    <field name="display_name" />
                </tree>
            '''
        })

        user_view_xml_id = self.env["ir.model.data"].create({
            "name": "studio_test_user_view",
            "model": "ir.ui.view",
            "module": "web_studio",
            "res_id": user_view.id,
        })

        self.testView.arch = '''<form>
            <field name="user_ids" context="{'tree_view_ref': '%s'}"/>
            <sheet>
                <notebook>
                    <page>
                        <field name="user_ids" context="{'tree_view_ref': '%s'}" />
                    </page>
                </notebook> 
            </sheet>
        </form>''' % (user_view_xml_id.complete_name, user_view_xml_id.complete_name)
        studio_view = _get_studio_view(self.testView)
        self.assertFalse(studio_view.exists())

        self.start_tour("/web?debug=tests", 'web_studio_enter_x2many_auto_inlined_subview_with_multiple_field_matching',
                        login="admin", timeout=200)
        studio_view = _get_studio_view(self.testView)

        assertViewArchEqual(self, studio_view.arch, """
            <data>
               <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]/field[@name='user_ids']" position="inside">
                 <tree class="test-user-list">
                   <field name="display_name" />
                   <field name="log_ids" optional="show" />
                 </tree>
               </xpath>
             </data>
            """)

    def test_field_with_group(self):
        operations = []
        def edit_view_mocked(*args, **kwargs):
            operations.extend(kwargs["operations"] if "operations" in kwargs else args[3])

        watch_edit_view(self, edit_view_mocked)

        doesNotHaveGroup = self.env["res.groups"].create({
            "name": "studio does not have"
        })
        doesNotHaveGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_doesnothavegroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": doesNotHaveGroup.id,
        })
        self.testView.write({
            "type": "tree",
            "arch": '''
                <tree>
                    <field name="display_name" />
                    <field name="employee" groups="{doesnothavegroup}" />
                    <field name="function" />
                    <field name="lang" />
                </tree>
            '''.format(doesnothavegroup=doesNotHaveGroupXmlId.complete_name)
        })
        self.testAction.write({
            "view_ids": [Command.clear(), Command.create({"view_id": self.testView.id, "view_mode": "tree"})]
        })

        self.start_tour("/web?debug=tests", 'web_studio_field_with_group', login="admin", timeout=200)

        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["target"]["xpath_info"], [{'tag': 'tree', 'indice': 1}, {'tag': 'field', 'indice': 3}])
        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, """
             <data>
                <xpath expr="//field[@name='function']" position="after">
                    <field name="website" optional="show"/>
                </xpath>
            </data>
        """)

    def test_studio_no_fetch_subview(self):

        doesNotHaveGroup = self.env["res.groups"].create({
            "name": "studio does not have"
        })
        doesNotHaveGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_doesnothavegroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": doesNotHaveGroup.id,
        })

        def create_new_field_mocked(*args, **kwargs):
            # For this test we need to patch groups from the phone field. Unfortunately it seems
            # that the patch is erased each time we create a new field so we have to patch after.
            self.patch(type(self.env["res.partner"]).phone, "groups", doesNotHaveGroupXmlId.complete_name)

        watch_create_new_field(self, create_new_field_mocked)
        self.patch(type(self.env["res.partner"]).phone, "groups", doesNotHaveGroupXmlId.complete_name)

        self.testView.write({
            "arch": '''
                <form>
                    <group>
                        <field name="name"/>
                    </group>
                </form>
            '''
        })

        self.start_tour("/web", 'web_studio_no_fetch_subview', login="admin")

    def test_elements_with_groups_form(self):
        operations = []
        def edit_view_mocked(*args, **kwargs):
            operations.extend(kwargs["operations"] if "operations" in kwargs else args[3])

        watch_edit_view(self, edit_view_mocked)

        doesNotHaveGroup = self.env["res.groups"].create({
            "name": "studio does not have"
        })
        doesNotHaveGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_doesnothavegroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": doesNotHaveGroup.id,
        })

        hasGroup = self.env["res.groups"].create({
            "name": "studio has group",
            "users": [Command.link(2)]
        })
        hasGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_hasgroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": hasGroup.id,
        })

        self.patch(type(self.env["res.partner"]).function, "groups", doesNotHaveGroupXmlId.complete_name)

        self.testView.write({
            "arch": '''
                <form>
                    <group>
                        <field name="function" groups="{hasgroup}" />
                        <field name="employee" groups="{doesnothavegroup}" />
                        <field name="display_name" />
                    </group>
                </form>
            '''.format(doesnothavegroup=doesNotHaveGroupXmlId.complete_name, hasgroup=hasGroupXmlId.complete_name)
        })
        self.start_tour("/web", 'web_studio_elements_with_groups_form', login="admin", timeout=600000)
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["target"]["xpath_info"], [{'indice': 1, 'tag': 'form'}, {'indice': 1, 'tag': 'group'}, {'indice': 3, 'tag': 'field'}])
        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, """
            <data>
               <xpath expr="//field[@name='display_name']" position="after">
                 <field name="website"/>
               </xpath>
            </data>
        """)

    def test_element_group_in_sidebar(self):
        group = self.env["res.groups"].create({
            "name": "Test Group",
            "users": [Command.link(2)]
        })
        groupXmlId = self.env["ir.model.data"].create({
            "name": "test_group",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": group.id,
        })

        self.testView.write({
            "arch": '''
                <form>
                    <field name="display_name" groups="{group}" />
                </form>
            '''.format(group=groupXmlId.complete_name)
        })
        self.start_tour("/web?debug=tests", 'test_element_group_in_sidebar', login="admin", timeout=600000)

    def test_create_one2many_lines_then_edit_name(self):
        self.testView.arch = '''
        <form>
            <group>
                <field name="name" />
            </group>
        </form>
        '''

        custom_fields_before_studio = self.env["ir.model.fields"].search([
            ("state", "=", "manual"),
        ])

        self.start_tour("/web?debug=tests", 'web_studio_test_create_one2many_lines_then_edit_name', login="admin", timeout=30000)

        custom_fields = self.env["ir.model.fields"].search_read([
            ("state", "=", "manual"),
            ("id", "not in", custom_fields_before_studio.ids),
        ], fields=["name", "ttype", "field_description"])

        self.maxDiff = None
        self.assertCountEqual(
            [{key: val for key, val in field.items() if key != 'id'} for field in custom_fields],
            [
                {"name": "x_studio_new_name", 'ttype': 'one2many', 'field_description': 'new name'},
                {"name": "x_name", 'ttype': 'char', 'field_description': 'Description'},
                {"name": "x_res_partner_id", 'ttype': 'many2one', 'field_description': 'X Res Partner'},
                {"name": "x_studio_sequence", 'ttype': 'integer', 'field_description': 'Sequence'},
            ]
        )

    def test_address_view_id_no_edit(self):
        self.testView.write({
            "arch": '''
                <form>
                    <div class="o_address_format">
                        <field name="lang"/>
                    </div>
                </form>
            '''
        })
        self.env.company.country_id.address_view_id = self.env.ref('base.view_partner_address_form')
        self.start_tour("/web?debug=tests", 'web_studio_test_address_view_id_no_edit', login="admin", timeout=200)

    def test_custom_selection_field_edit_values(self):
        self.testView.arch = '''
             <form>
                 <group>
                     <field name="name" />
                 </group>
             </form>
        '''

        self.start_tour("/web?debug=tests", 'web_studio_custom_selection_field_edit_values', login="admin", timeout=200)
        selection_field = self.env["ir.model.fields"].search(
            [
                ("state", "=", "manual"),
                ("model", "=", "res.partner"),
                ("ttype", "=", "selection")
            ],
            limit=1
        )

        self.assertEqual(selection_field.selection_ids.mapped("name"), ["some value", "another value"])

    def test_create_new_model_from_existing_view(self):
        self.testView.write({
            "model": "res.users",
            "type": "kanban",
            "arch": '''<kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_details">
                            <field name="display_name"/>
                        </div>
                    </t>
                </templates>
            </kanban>
            '''
        })
        self.testAction.view_ids.view_mode = "kanban"
        self.start_tour("/web?debug=tests", 'web_studio_test_create_new_model_from_existing_view', login="admin",
                        timeout=200)

    def test_create_model_with_clickable_stages(self):
        self.start_tour("/web?debug=tests", 'web_studio_test_create_model_with_clickable_stages', login="admin", timeout=200)

    def test_enter_x2many_edition_with_multiple_subviews(self):
        doesNotHaveGroup = self.env["res.groups"].create({
            "name": "studio does not have"
        })
        doesNotHaveGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_doesnothavegroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": doesNotHaveGroup.id,
        })

        hasGroup = self.env["res.groups"].create({
            "name": "studio has group",
            "users": [Command.link(2)]
        })
        hasGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_hasgroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": hasGroup.id,
        })

        self.testView.arch = '''
            <form>
                <field name="name"/>
                <field name="child_ids">
                    <tree groups="{hasgroup}">
                        <field name="type"/>
                    </tree>
                    <tree groups="{doesnothavegroup}">
                        <field name="name"/>
                    </tree>
                </field>
            </form>
        '''.format(doesnothavegroup=doesNotHaveGroupXmlId.complete_name, hasgroup=hasGroupXmlId.complete_name)
        self.start_tour("/web?debug=tests", 'web_studio_test_enter_x2many_edition_with_multiple_subviews',
                        login="admin", timeout=200)

    def test_enter_x2many_edition_with_multiple_subviews_correct_xpath(self):
        operations = []
        def edit_view_mocked(*args, **kwargs):
            operations.extend(kwargs["operations"] if "operations" in kwargs else args[3])

        watch_edit_view(self, edit_view_mocked)

        doesNotHaveGroup = self.env["res.groups"].create({
            "name": "studio does not have"
        })
        doesNotHaveGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_doesnothavegroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": doesNotHaveGroup.id,
        })

        hasGroup = self.env["res.groups"].create({
            "name": "studio has group",
            "users": [Command.link(2)]
        })
        hasGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_hasgroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": hasGroup.id,
        })

        self.testView.arch = '''
              <form>
                  <field name="name"/>
                  <field name="child_ids">
                      <tree groups="{doesnothavegroup}" class="test-subview-list">
                          <field name="name"/>
                      </tree>
                      <tree groups="{hasgroup}" class="test-subview-list">
                          <field name="name"/>
                      </tree>
                  </field>
              </form>
        '''.format(doesnothavegroup=doesNotHaveGroupXmlId.complete_name, hasgroup=hasGroupXmlId.complete_name)
        self.start_tour("/web?debug=tests", 'web_studio_test_enter_x2many_edition_with_multiple_subviews_correct_xpath',
                        login="admin", timeout=200)
        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, """
            <data>
               <xpath expr="//form[1]/field[@name='child_ids']/tree[2]/field[@name='name']" position="before">
                 <field name="active" optional="show"/>
               </xpath>
            </data>
        """)
        self.assertEqual(len(operations), 1)
        self.assertDictEqual(operations[0], {
            'type': 'add',
            'target': {
                'tag': 'field',
                'attrs': {
                    'name': 'name'
                },
                'xpath_info': [
                    {
                        'tag': 'tree',
                        'indice': 2
                    },
                    {
                        'tag': 'field',
                        'indice': 1
                    },
                ],
                'subview_xpath': "/form[1]/field[2]/tree[2]",
            },
            'position': 'before',
            'node': {
                'tag': 'field',
                'attrs': {
                    'name': 'active',
                    'optional': 'show'
                }
            }
        })

    def test_studio_arch_has_measure_field_ids(self):
        view = self.env["ir.ui.view"].create({
            "name": "simple view",
            "model": "res.partner",
            "type": "pivot",
            "arch": '''
                <pivot>
                    <field name="display_name" type="measure"/>
                </pivot>
            '''
        })

        studio_view = self.env[view.model].with_context(studio=True).get_view(view.id, view.type)
        field_id = self.env['ir.model.fields'].search([('model', '=', view.model), ('name', 'in', ['display_name'])]).ids[0]

        assertViewArchEqual(self, studio_view["arch"], '''
            <pivot studio_pivot_measure_field_ids="[{field_id}]">
                <field name="display_name" type="measure"/>
            </pivot>
        '''.format(field_id=field_id))

    def test_field_with_groups_in_tree_node_has_groups_too(self):
        # The field has a group in python in which the user is
        # The node has also a group in which the user is not
        hasGroup = self.env["res.groups"].create({
            "name": "studio has group",
            "users": [Command.link(self.env.user.id)]
        })
        hasGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_hasgroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": hasGroup.id,
        })

        doesNotHaveGroup = self.env["res.groups"].create({
            "name": "studio does not have"
        })
        doesNotHaveGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_doesnothavegroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": doesNotHaveGroup.id,
        })

        self.patch(type(self.env["res.partner"]).title, "groups", hasGroupXmlId.complete_name)

        view = self.env["ir.ui.view"].create({
            "name": "simple view",
            "model": "res.partner",
            "type": "tree",
            "arch": '''
                <tree>
                    <field name="display_name"/>
                    <field name="title" groups="{doesnothavegroup}" />
                </tree>
            '''.format(doesnothavegroup=doesNotHaveGroupXmlId.complete_name)
        })
        arch = self.env[view.model].with_context(studio=True).get_view(view.id, view.type)["arch"]

        studio_groups = json.dumps([{
            "id": doesNotHaveGroup.id,
            "name": doesNotHaveGroup.name,
            "display_name": doesNotHaveGroup.display_name,
        }])

        xml_temp = E.field(name="title", column_invisible="True", groups=doesNotHaveGroupXmlId.complete_name, studio_groups=studio_groups)

        expected = '''
            <tree>
               <field name="display_name"/>
               {xml_stringified}
             </tree>
        '''.format(xml_stringified=etree.tostring(xml_temp).decode("utf-8"))

        assertViewArchEqual(self, arch, expected)

    def test_set_tree_column_conditional_invisibility(self):
        self.testViewList = self.env["ir.ui.view"].create({
            "name": "simple partner",
            "model": "res.partner",
            "type": "tree",
            "arch": '''
                <tree>
                    <field name="display_name" />
                    <field name="title" />
                </tree>
            '''
        })
        self.testAction.write({
            "view_ids": [
                Command.clear(),
                Command.create({"view_id": self.testViewList.id, "view_mode": "tree"}),
            ]
        })
        self.start_tour("/web?debug=tests", 'web_studio_set_tree_node_conditional_invisibility', login="admin", timeout=200)
        arch = self.env[self.testViewList.model].with_context(studio=True).get_view(self.testViewList.id, self.testViewList.type)["arch"]
        expected = '''
            <tree>
                <field name="display_name"/>
                <field name="title" invisible="{title_modifiers}"/>
             </tree>
        '''.format(title_modifiers="display_name == &quot;Robert&quot;")

        assertViewArchEqual(self, arch, expected)

    def test_studio_view_is_last(self):
        # The studio view created should have, in all cases, a priority greater than all views
        # that are part of the inheritance
        self.testView.arch = '''
            <form><sheet>
                <group><field name="name" /></group>
            </sheet></form>
        '''

        self.env["ir.ui.view"].create({
            "name": "simple view inherit",
            "inherit_id": self.testView.id,
            "mode": "extension",
            "priority": 123,
            "model": "res.partner",
            "type": "form",
            "arch": '''
                <data>
                <xpath expr="//field[@name='name']" position="after">
                    <field name="title" />
                </xpath>
                </data>
            '''
        })

        self.start_tour("/web?debug=tests", 'web_studio_test_studio_view_is_last', login="admin", timeout=200)
        studioView = _get_studio_view(self.testView)
        self.assertEqual(studioView.priority, 1230)

        self.maxDiff = None
        assertViewArchEqual(self, studioView["arch"], '''
            <data>
                <xpath expr="//field[@name='title']" position="after">
                  <field name="website"/>
                </xpath>
            </data>
        ''')

    def test_edit_form_subview_attributes(self):
        self.testView.arch = '''
            <form>
                <field name="child_ids">
                    <form class="test-subview-form">
                        <field name="display_name" />
                    </form>
                </field>
            </form>
        '''

        self.start_tour("/web?debug=tests", 'web_studio_test_edit_form_subview_attributes', login="admin", timeout=200)

        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, """
            <data>
                <xpath expr="//form[1]/field[@name='child_ids']/form[1]" position="attributes">
                    <attribute name="create">false</attribute>
                </xpath>
            </data>""")

    def test_x2many_two_levels_edition(self):
        self.testView.arch = '''
        <form>
            <field name="display_name"/>
            <field name="user_ids">
                <form class="test-subview-form-1">
                    <group>
                        <field name="display_name"/>
                        <field name="log_ids">
                            <form invisible="1" class="test-subview-form-2"/>
                            <form class="test-subview-form-2">
                                <group><field name="display_name"/></group>
                            </form>
                        </field>
                    </group>
                </form>
            </field>
        </form>'''

        self.start_tour("/web?debug=tests", 'web_studio_x2many_two_levels_edition', login="admin", timeout=200)

        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, '''
            <data>
            <xpath expr="//form[1]/field[@name='user_ids']/form[1]/group[1]/field[@name='log_ids']/form[2]/group[1]/field[@name='display_name']" position="before">
             <field name="create_date"/>
            </xpath>
            </data>
        ''')

    def test_field_group_studio_no_fetch(self):
        doesNotHaveGroup = self.env["res.groups"].create({
            "name": "studio does not have"
        })
        doesNotHaveGroupXmlId = self.env["ir.model.data"].create({
            "name": "studio_test_doesnothavegroup",
            "model": "res.groups",
            "module": "web_studio",
            "res_id": doesNotHaveGroup.id,
        })
        self.patch(type(self.env["res.partner"]).function, "groups", doesNotHaveGroupXmlId.complete_name)

        self.testViewForm = self.env["ir.ui.view"].create({
            "name": "simple partner",
            "model": "res.partner",
            "type": "form",
            "arch": '''
                <form>
                    <field name="function" />
                    <field name="name" />
                </form>
            '''
        })
        self.testViewList = self.env["ir.ui.view"].create({
            "name": "simple partner",
            "model": "res.partner",
            "type": "tree",
            "arch": '''
                <tree>
                    <field name="function" />
                    <field name="name" />
                </tree>
            '''
        })
        self.testViewKanban = self.env["ir.ui.view"].create({
            "name": "simple partner",
            "model": "res.partner",
            "type": "kanban",
            "arch": '''
                <kanban>
                    <t t-name="kanban-box">
                        <field name="function" />
                        <field name="name" />
                    </t>
                </kanban>
            '''
        })
        self.testAction.write({
            "view_ids": [
                Command.clear(),
                Command.create({"view_id": self.testViewForm.id, "view_mode": "form"}),
                Command.create({"view_id": self.testViewList.id, "view_mode": "tree"}),
                Command.create({"view_id": self.testViewKanban.id, "view_mode": "kanban"}),
            ]
        })
        self.start_tour("/web?debug=tests", 'web_studio_field_group_studio_no_fetch', login="admin", timeout=200)


    def test_monetary_create(self):
        self.create_empty_app()
        self.newView.arch = '''<form>
            <group>
                <field name="x_name"/>
            </group>
        </form>'''
        self.start_tour("/web?debug=tests", 'web_studio_monetary_create', login="admin")

        # There is a new currency and there is a new monetary
        fields = self.env[self.newModel.model]._fields
        currency_name_list = list(filter(lambda key: fields[key]._description_type == 'many2one' and fields[key]._description_relation == 'res.currency', fields.keys()))
        monetary_name_list = list(filter(lambda key: fields[key].type == 'monetary', fields.keys()))
        self.assertEqual(len(currency_name_list), 1)
        self.assertEqual(len(monetary_name_list), 1)

        # The studio arch contains the new monetary and the new currency
        studioView = _get_studio_view(self.newView)
        assertViewArchEqual(self, studioView.arch, f"""
            <data>
                <xpath expr="//field[@name='x_name']" position="before">
                    <field name="{monetary_name_list[0]}"/>
                    <field name="{currency_name_list[0]}"/>
                </xpath>
            </data>
            """)

    def test_monetary_change_currency_name(self):
        self.create_empty_app()
        currency = self.env["ir.model.fields"].create({
            "name": "x_studio_currency_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "many2one",
            "relation": "res.currency",
        })
        self.env["ir.model.fields"].create({
            "name": "x_studio_monetary_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "monetary",
            "currency_field": "x_studio_currency_test",
        })
        self.newView.arch = '''<form>
            <group>
                <field name="x_name"/>
                <field name="x_studio_currency_test"/>
                <field name="x_studio_monetary_test"/>
            </group>
        </form>'''
        self.start_tour("/web?debug=tests", 'web_studio_monetary_change_currency_name', login="admin")
        self.assertEqual(currency.field_description, "NewCurrency")

    def test_related_monetary_creation(self):
        res_partner_model_id = self.env["ir.model"].search([("model", "=", "res.partner")]).id
        self.create_empty_app()
        self.env["ir.model.fields"].create({
            "name": "x_studio_currency_test",
            "model": "res.partner",
            "model_id": res_partner_model_id,
            "ttype": "many2one",
            "relation": "res.currency",
        })
        self.env["ir.model.fields"].create({
            "name": "x_studio_monetary_test",
            "model": "res.partner",
            "model_id": res_partner_model_id,
            "ttype": "monetary",
            "currency_field": "x_studio_currency_test",
        })
        self.testView.arch = '''<form>
            <group>
                <field name="name"/>
                <field name="x_studio_currency_test"/>
                <field name="x_studio_monetary_test"/>
            </group>
        </form>'''

        self.env["ir.model.fields"].create({
            "name": "x_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "many2one",
            "relation": "res.partner",
        })
        self.newView.arch = '''
        <form>
            <group>
                <field name="x_name" />
                <field name="x_test"/>
            </group>
        </form>
        '''
        self.start_tour("/web?debug=tests", 'web_studio_related_monetary_creation', login="admin")
        # There is only one currency and there is a new monetary
        fields = self.env["x_test_model"]._fields
        currency_name_list = list(filter(lambda key: fields[key]._description_type == 'many2one' and fields[key]._description_relation == 'res.currency', fields.keys()))
        monetary_name_list = list(filter(lambda key: fields[key].type == 'monetary', fields.keys()))
        self.assertEqual(len(currency_name_list), 1)
        self.assertEqual(len(monetary_name_list), 1)
        # The monetary has been created and is a related field
        self.assertEqual(self.env['x_test_model']._fields[monetary_name_list[0]].related, "x_test.x_studio_monetary_test")
        # A currency has been created because there was none in the model/view
        self.assertEqual(currency_name_list[0], 'x_studio_currency_id')

    def test_monetary_change_currency_field(self):
        self.create_empty_app()
        self.env["ir.model.fields"].create({
            "name": "x_studio_currency_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "many2one",
            "relation": "res.currency",
        })
        self.env["ir.model.fields"].create({
            "name": "x_studio_currency_test2",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "many2one",
            "relation": "res.currency",
        })
        monetary = self.env["ir.model.fields"].create({
            "name": "x_studio_monetary_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "monetary",
            "currency_field": "x_studio_currency_test",
        })
        self.newView.arch = '''<form>
            <group>
                <field name="x_name"/>
                <field name="x_studio_currency_test"/>
                <field name="x_studio_currency_test2"/>
                <field name="x_studio_monetary_test"/>
            </group>
        </form>'''
        self.start_tour("/web?debug=tests", 'web_studio_monetary_change_currency_field', login="admin")

        # The currency_field in the monetary field changed
        self.assertEqual(monetary.currency_field, 'x_studio_currency_test2')

    def test_monetary_change_currency_not_in_view(self):
        self.create_empty_app()
        self.env["ir.model.fields"].create({
            "name": "x_studio_currency_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "many2one",
            "relation": "res.currency",
        })
        self.env["ir.model.fields"].create({
            "name": "x_studio_currency_test2",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "many2one",
            "relation": "res.currency",
        })
        monetary = self.env["ir.model.fields"].create({
            "name": "x_studio_monetary_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "monetary",
            "currency_field": "x_studio_currency_test",
        })
        self.newView.arch = '''<form>
            <group>
                <field name="x_name"/>
                <field name="x_studio_currency_test"/>
                <field name="x_studio_monetary_test"/>
            </group>
        </form>'''
        self.start_tour("/web?debug=tests", 'web_studio_monetary_change_currency_not_in_view', login="admin")

        # The currency_field in the monetary field changed
        self.assertEqual(monetary.currency_field, 'x_studio_currency_test2')

        studioView = _get_studio_view(self.newView)
        assertViewArchEqual(self, studioView.arch, """
            <data>
                <xpath expr="//field[@name='x_studio_monetary_test']" position="after">
                    <field name="x_studio_currency_test2"/>
                </xpath>
            </data>
            """)

    def test_monetary_add_existing_monetary(self):
        self.create_empty_app()
        self.env["ir.model.fields"].create({
            "name": "x_studio_currency_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "many2one",
            "relation": "res.currency",
        })
        self.env["ir.model.fields"].create({
            "name": "x_studio_monetary_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "monetary",
            "currency_field": "x_studio_currency_test",
        })
        self.newView.arch = '''<form>
            <group>
                <field name="x_name"/>
            </group>
        </form>'''
        self.start_tour("/web?debug=tests", 'web_studio_monetary_add_existing_monetary', login="admin")

        # The studio arch contains the monetary and the associated currency
        studioView = _get_studio_view(self.newView)
        assertViewArchEqual(self, studioView.arch, """
            <data>
                <xpath expr="//field[@name=\'x_name\']" position="before">
                    <field name="x_studio_monetary_test"/>
                    <field name="x_studio_currency_test"/>
                </xpath>
            </data>
            """)

    def test_monetary_create_monetary_with_existing_currency(self):
        self.create_empty_app()
        self.env["ir.model.fields"].create({
            "name": "x_studio_currency_test",
            "model": "x_test_model",
            "model_id": self.newModel.id,
            "ttype": "many2one",
            "relation": "res.currency",
        })
        self.newView.arch = '''<form>
            <group>
                <field name="x_name"/>
                <field name="x_studio_currency_test"/>
            </group>
        </form>'''
        self.start_tour("/web?debug=tests", 'web_studio_monetary_create_monetary_with_existing_currency', login="admin")

        # There is only one currency and there is a new monetary
        fields = self.env[self.newModel.model]._fields
        currency_name_list = list(filter(lambda key: fields[key]._description_type == 'many2one' and fields[key]._description_relation == 'res.currency', fields.keys()))
        monetary_name_list = list(filter(lambda key: fields[key].type == 'monetary', fields.keys()))
        self.assertEqual(len(currency_name_list), 1)
        self.assertEqual(len(monetary_name_list), 1)

        # The studio arch contains the new monetary but no currency as it exist in the original arch
        studioView = _get_studio_view(self.newView)
        assertViewArchEqual(self, studioView.arch, f"""
            <data>
                <xpath expr="//field[@name=\'x_name\']" position="after">
                    <field name="{monetary_name_list[0]}"/>
                </xpath>
            </data>
            """)

    def test_move_similar_field(self):
        self.testView.arch = '''
            <form>
                <sheet>
                    <group><group>
                        <field name="active" />
                    </group></group>
                    <notebook>
                        <page string="one">
                            <group><group><field name="display_name" /></group></group>
                        </page>
                        <page string="two">
                            <group><group><field name="display_name" /></group></group>
                        </page>
                   </notebook>
                </sheet>
            </form>
        '''

        self.start_tour("/web?debug=tests", 'web_studio_test_move_similar_field', login="admin", timeout=400)

        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, '''
        <data>
            <xpath expr="//field[@name='active']" position="before">
                <xpath expr="//form[1]/sheet[1]/notebook[1]/page[2]/group[1]/group[1]/field[@name='display_name']" position="move" />
            </xpath>
        </data>
        ''')

    def create_user_view(self):
        self.testView.write({
            "name": "simple user",
            "model": "res.users",
            "arch": '''
                <form>
                    <group>
                        <field name="name"/>
                    </group>
                </form>
            '''
        })
        self.testAction.write({
            "name": "simple user",
            "res_model": "res.users",
        })
        self.testActionXmlId.name = "studio_test_user_action"
        self.testMenu.name = "Studio Test User"
        self.testMenuXmlId.name = "studio_test_user_menu"

    def test_related_binary_field_with_filename(self):
        self.create_user_view()

        partner_field = self.env["ir.model.fields"].create({
            "field_description": "New File",
            "name": "x_new_file",
            "ttype": "binary",
            "model": "res.partner",
            "model_id": self.env["ir.model"]._get('res.partner').id,
            "state": "manual",
        })
        self.env["ir.model.fields"].create({
            "field_description": "New File filename",
            "name": "x_new_file_filename",
            "ttype": "char",
            "model": "res.partner",
            "model_id": self.env["ir.model"]._get('res.partner').id,
            "state": "manual",
        })

        self.start_tour("/web?debug=tests", 'web_studio_test_related_file', login="admin", timeout=400)

        studioView = _get_studio_view(self.testView)
        binary_field = self.env["ir.model.fields"].search([('model', '=', 'res.users'), ('ttype', '=', 'binary'), ('name', 'like', 'x_studio_related')])
        self.assertEqual(len(binary_field), 1)
        self.assertEqual(binary_field.related_field_id, partner_field)
        assertViewArchEqual(self, studioView.arch,
        '''
        <data>
            <xpath expr="//form[1]/group[1]/field[@name=\'name\']" position="before">
                <field filename="{binary_field.name}_filename" name="{binary_field.name}"/>
                <field invisible="True" name="{binary_field.name}_filename"/>
            </xpath>
        </data>
        '''.format(binary_field=binary_field))

    def test_nested_related_binary_field_with_filename(self):
        self.create_user_view()

        self.env["ir.model.fields"].create({
            "field_description": "New File",
            "name": "x_new_file",
            "ttype": "binary",
            "model": "res.partner.category",
            "model_id": self.env["ir.model"]._get('res.partner.category').id,
            "state": "manual",
        })
        self.env["ir.model.fields"].create({
            "field_description": "New File filename",
            "name": "x_new_file_filename",
            "ttype": "char",
            "model": "res.partner.category",
            "model_id": self.env["ir.model"]._get('res.partner.category').id,
            "state": "manual",
        })

        partner_field = self.env["ir.model.fields"].create({
            "field_description": "New File",
            "name": "x_new_related_file",
            "ttype": "binary",
            "model": "res.partner",
            "model_id": self.env["ir.model"]._get('res.partner').id,
            "state": "manual",
            "related": "category_id.x_new_file"
        })
        self.env["ir.model.fields"].create({
            "field_description": "New File filename",
            "name": "x_new_related_file_filename",
            "ttype": "char",
            "model": "res.partner",
            "model_id": self.env["ir.model"]._get('res.partner').id,
            "state": "manual",
            "related": "category_id.x_new_file_filename"
        })

        self.start_tour("/web?debug=tests", 'web_studio_test_related_file', login="admin", timeout=400)

        studioView = _get_studio_view(self.testView)
        binary_field = self.env["ir.model.fields"].search([('model', '=', 'res.users'), ('ttype', '=', 'binary'), ('name', 'like', 'x_studio_related')])
        self.assertEqual(len(binary_field), 1)
        self.assertEqual(binary_field.related_field_id, partner_field)
        assertViewArchEqual(self, studioView.arch,
        '''
        <data>
            <xpath expr="//form[1]/group[1]/field[@name=\'name\']" position="before">
                <field filename="{binary_field.name}_filename" name="{binary_field.name}"/>
                <field invisible="True" name="{binary_field.name}_filename"/>
            </xpath>
        </data>
        '''.format(binary_field=binary_field))

    def test_related_binary_field_without_filename(self):
        self.create_user_view()

        partner_field = self.env["ir.model.fields"].create({
            "field_description": "New File",
            "name": "x_new_file",
            "ttype": "binary",
            "model": "res.partner",
            "model_id": self.env["ir.model"]._get('res.partner').id,
            "state": "manual",
        })

        self.start_tour("/web?debug=tests", 'web_studio_test_related_file', login="admin", timeout=400)

        studioView = _get_studio_view(self.testView)
        binary_field = self.env["ir.model.fields"].search([('model', '=', 'res.users'), ('ttype', '=', 'binary'), ('name', 'like', 'x_studio_related')])
        self.assertEqual(len(binary_field), 1)
        self.assertEqual(binary_field.related_field_id, partner_field)
        assertViewArchEqual(self, studioView.arch,
        '''
        <data>
            <xpath expr="//form[1]/group[1]/field[@name=\'name\']" position="before">
                <field name="{binary_field.name}"/>
            </xpath>
        </data>
        '''.format(binary_field=binary_field))

    def test_undo_new_field(self):
        self.testView.arch = '''
        <form>
            <group>
                <field name="name" />
            </group>
        </form>
        '''
        self.start_tour("/web?debug=tests", "web_studio_test_undo_new_field", login="admin", timeout=200)

    def test_change_lone_attr_modifier_form(self):
        self.testView.arch = """<form><field name='name' required="not context.get('something')"/></form>"""
        self.start_tour("/web?debug=tests", "web_studio_test_change_lone_attr_modifier_form", login="admin")
        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, '''
        <data>
          <xpath expr="//form[1]/field[@name='name']" position="attributes">
             <attribute name="required">False</attribute>
          </xpath>
        </data>
        ''')

    def test_drag_and_drop_boolean(self):
        self.testView.arch = '''
             <form>
                 <group>
                    <field name="name" />
                 </group>
             </form>
        '''

        self.start_tour("/web?debug=tests", 'web_studio_boolean_field_drag_and_drop', login="admin", timeout=200)

        studioView = _get_studio_view(self.testView)
        boolean_field = self.env['ir.model.fields'].search([('name', 'like', 'x_studio_boolean')])[0]

        assertViewArchEqual(self, studioView.arch, '''
             <data>
                <xpath expr="//form[1]/group[1]/field[@name='name']" position="after">
                    <field name="{boolean_field.name}"/>
                </xpath>
            </data>
        '''.format(boolean_field=boolean_field))

    def test_new_field_rename_description(self):
        self.testView.arch = '''
             <form>
                 <group>
                    <field name="name" />
                 </group>
             </form>
        '''

        self.start_tour("/web", "web_studio_test_new_field_rename_description", login="admin")
        new_field = self.env["ir.model.fields"]._get("res.partner", "x_studio_my_new_field")
        self.assertEqual(new_field.field_description, "my new field")
        studioView = _get_studio_view(self.testView)
        self.assertXMLEqual(studioView.arch, """
            <data>
                <xpath expr="//form[1]/group[1]/field[@name='name']" position="after">
                   <field name="x_studio_my_new_field"/>
                </xpath>
            </data>
        """)

    def test_edit_digits_option(self):
        self.testView.arch = '''<form class="test-user-list">
            <field name="partner_latitude" />
        </form>'''
        self.start_tour("/web?debug=tests", 'web_studio_test_edit_digits_option', login="admin", timeout=200)
        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, """
            <data>
                <xpath expr="//field[@name='partner_latitude']" position="attributes">
                    <attribute name="options">{"digits":[4,2]}</attribute>
                </xpath>
             </data>
            """)

    def test_button_rainbow_effect(self):
        self.testView.arch = """<form><button type="object" name="open_commercial_entity">Button</button></form>"""
        self.start_tour("/web", "web_studio.test_button_rainbow_effect", login="admin")

        studioView = _get_studio_view(self.testView)
        attachment = self.env["ir.attachment"].search([("name", "=", "my_studio_image.png")])

        self.assertXMLEqual(studioView.arch, """
        <data>
          <xpath expr="//button[@name='open_commercial_entity']" position="attributes">
            <attribute name="effect">{'img_url': '/web/content/%s'}</attribute>
          </xpath>
        </data>
        """ % attachment.id)

    def test_context_write_cleaned(self):
        view = self.env["ir.ui.view"].create({
            "model": "res.users",
            "type": "form",
            "arch": """<form>
                <div class="oe_button_box"/>
                <field name="display_name" invisible="context.get('default_type')" />
            </form>"""
        })

        operations = [
            {
                "type": "add",
                "target": {
                    "tag": "div",
                    "attrs": {
                        "class": "oe_button_box"
                    }
                },
                "position": "inside",
                "node": {
                    "tag": "button",
                    "field": self.env["ir.model.fields"]._get("res.partner", "user_id").id,
                    "string": "Test studio new button",
                    "attrs": {
                        "class": "oe_stat_button",
                        "icon": "fa-diamond"
                    }
                }
            }
        ]
        create_action = self.env.registry["ir.actions.actions"]._create
        action_created = False
        def mock_act_create(rec_set, *args, **kwargs):
            nonlocal action_created
            action_created = True
            context = dict(rec_set.env.context)
            del context["tz"]
            self.assertEqual(context, {'lang': 'en_US', 'uid': 2, 'arbitrary_key': 'arbitrary', "studio": 1})
            return create_action(rec_set, *args, **kwargs)

        self.patch(self.env.registry["ir.actions.actions"], "_create", mock_act_create)

        self.authenticate("admin", "admin")
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            response = self.url_open("/web_studio/edit_view",
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "params": {
                        "view_id": view.id,
                        "studio_view_arch": "",
                        "model": "res.users",
                        "operations": operations,
                        "context": {
                            "default_type": "some_type",
                            "arbitrary_key": "arbitrary",
                            "studio": 1,
                        }
                    },
            }))
        action = self.env["ir.actions.act_window"].search([("res_model", "=", "res.partner")], order="create_date DESC", limit=1)

        self.assertTrue(action_created, True)
        self.assertEqual(action.type, "ir.actions.act_window")
        self.assertEqual(action.name, "Test studio new button")
        self.assertXMLEqual(response.json()["result"]["views"]["form"]["arch"], f"""
        <form>
          <div class="oe_button_box">
            <button class="oe_stat_button" icon="fa-diamond" type="action" name="{action.xml_id}">
              <field widget="statinfo" name="x_user_id_res_partner_count" string="Test studio new button"/>
            </button>
          </div>
          <field name="display_name" invisible="context.get('default_type')"/>
        </form>
        """)

    def test_res_users_fake_fields(self):
        user_fields = self.env["res.users"].fields_get()
        assertable = [field["string"] for field in user_fields.values() if field["string"] in ("Administration", "Multi Companies")]
        self.assertEqual(len(assertable), 2)

        action = self.env.ref("base.action_res_users")
        url = f"/web?debug=1#action=studio&mode=editor&_tab=views&_view_type=list&_action={action.id}"
        self.start_tour(url, 'web_studio.test_res_users_fake_fields', login="admin")

    def test_add_button_xml_id(self):
        base_view = self.env["ir.ui.view"].create({
            "name": "test_partner_simple",
            "model": "res.partner",
            "mode": "primary",
            "type": "form",
            "arch": """<form><sheet><div class="oe_button_box"></div></sheet></form>"""
        })

        operations = [
            {
                "type": "add",
                "target": {
                    "tag": "div",
                    "attrs": {
                        "class": "oe_button_box"
                    }
                },
                "view_id": base_view.id,
                "position": "inside",
                "node": {
                    "tag": "button",
                    "field": self.env["ir.model.fields"]._get("res.partner", "parent_id").id,
                    "string": "aa",
                    "attrs": {
                        "class": "oe_stat_button",
                        "icon": "fa-diamond"
                    }
                }
            }
        ]

        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            self.authenticate("admin", "admin")
            self.url_open("/web_studio/edit_view", data=json.dumps({
                "params": {
                    "view_id": base_view.id,
                    "model": "res.partner",
                    "studio_view_arch": "<data />",
                    "operations": operations,
                    "context": {"studio": 1},
                }
            }), headers={"Content-Type": "application/json"})

        action = self.env["ir.actions.act_window"].search([], limit=1, order="create_date DESC")
        self.assertTrue(action.xml_id.startswith("studio_customization."))
        form = base_view.get_combined_arch()
        self.assertXMLEqual(form, f"""
        <form>
           <sheet>
             <div class="oe_button_box">
               <button class="oe_stat_button" icon="fa-diamond" type="action" name="{action.xml_id}">
                 <field widget="statinfo" name="x_parent_id_res_partner_count" string="aa"/>
               </button>
             </div>
           </sheet>
        </form>
        """)

    def test_reload_after_restoring_default_view(self):
        self.start_tour("/web?debug=tests", 'web_studio_test_reload_after_restoring_default_view', login="admin")

    def test_edit_reified_field(self):
        # find some reified field name
        reified_fname = next(
            fname
            for fname in self.env["res.users"].fields_get()
            if fname.startswith(('in_group_', 'sel_groups_'))
        )

        self.testView.write({
            "name": "simple user",
            "model": "res.users",
            "arch": '''
                <form>
                    <field name="%s"/>
                </form>
            ''' % reified_fname
        })
        self.testAction.res_model = "res.users"
        self.start_tour("/web?debug=tests", 'web_studio_test_edit_reified_field', login="admin")
        studioView = _get_studio_view(self.testView)
        assertViewArchEqual(self, studioView.arch, """
            <data>
              <xpath expr="//field[@name='%s']" position="attributes">
                <attribute name="string">new name</attribute>
              </xpath>
            </data>
        """ % reified_fname)
