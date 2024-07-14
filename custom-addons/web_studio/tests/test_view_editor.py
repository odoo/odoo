import json

import odoo
from odoo import api
from odoo.tools import DotDict
from odoo.http import _request_stack
from odoo.tests.common import TransactionCase
from odoo.addons.web_studio.controllers.main import WebStudioController
from copy import deepcopy
from lxml import etree

class TestStudioController(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env = api.Environment(self.cr, odoo.SUPERUSER_ID, {'load_all_views': True})
        _request_stack.push(self)
        self.session = DotDict({'debug': ''})
        self.studio_controller = WebStudioController()

    def tearDown(self):
        super().tearDown()
        _request_stack.pop()

    def _transform_arch_for_assert(self, arch_string):
        parser = etree.XMLParser(remove_blank_text=True)
        arch_string = etree.fromstring(arch_string, parser=parser)
        return etree.tostring(arch_string, pretty_print=True, encoding='unicode')

    def assertViewArchEqual(self, original, expected):
        if original:
            original = self._transform_arch_for_assert(original)
        if expected:
            expected = self._transform_arch_for_assert(expected)
        self.assertEqual(original, expected)

    def update_context(self, **overrides):
        self.env = self.env(context=dict(self.env.context, **overrides))


class TestEditView(TestStudioController):

    def edit_view(self, base_view, studio_arch="", operations=None, model=None, context=None):
        _ops = None
        if isinstance(operations, list):
            _ops = []
            for op in operations:
                _ops.append(deepcopy(op))  # the edit view controller may alter objects in place
        if studio_arch == "":
            studio_arch = "<data/>"
        return self.studio_controller.edit_view(base_view.id, studio_arch, _ops, model, context)

    def test_edit_view_binary_and_attribute(self):
        base_view = self.env['ir.ui.view'].create({
            'name': 'TestForm',
            'type': 'form',
            'model': 'res.partner',
            'arch': """
                <form>
                    <field name="display_name" />
                </form>"""
        })

        add_binary_op = {
            'type': 'add',
            'target': {'tag': 'field',
                       'attrs': {'name': 'display_name'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 1}]},
            'position': 'after',
            'node': {'tag': 'field',
                     'attrs': {},
                     'field_description': {'type': 'binary',
                                           'field_description': 'New File',
                                           'name': 'x_studio_binary_field_WocAO',
                                           'model_name': 'res.partner'}}
        }

        self.edit_view(base_view, operations=[add_binary_op])
        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
              <form>
                <field name="display_name"/>
                <field filename="x_studio_binary_field_WocAO_filename" name="x_studio_binary_field_WocAO"/>
                <field invisible="True" name="x_studio_binary_field_WocAO_filename"/>
              </form>
            """
        )

        add_widget_op = {
            'type': 'attributes',
            'target': {'tag': 'field',
                       'attrs': {'name': 'x_studio_binary_field_WocAO'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 2}]},
            'position': 'attributes',
            'node': {'tag': 'field',
                     'attrs': {'filename': 'x_studio_binary_field_WocAO_filename',
                               'name': 'x_studio_binary_field_WocAO',
                               'id': 'x_studio_binary_field_WocAO'},
                     'children': [],
                     'has_label': True},
            'new_attrs': {'widget': 'pdf_viewer', 'options': ''}
        }

        ops = [
            add_binary_op,
            add_widget_op
        ]
        self.edit_view(base_view, operations=ops)
        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
              <form>
                <field name="display_name"/>
                <field filename="x_studio_binary_field_WocAO_filename" name="x_studio_binary_field_WocAO" widget="pdf_viewer"/>
                <field invisible="True" name="x_studio_binary_field_WocAO_filename"/>
              </form>
            """
        )

    def test_edit_view_binary_and_attribute_then_remove_binary(self):
        base_view = self.env['ir.ui.view'].create({
            'name': 'TestForm',
            'type': 'form',
            'model': 'res.partner',
            'arch': """
                <form>
                    <field name="display_name" />
                </form>"""
        })

        add_binary_op = {
            'type': 'add',
            'target': {'tag': 'field',
                       'attrs': {'name': 'display_name'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 1}]},
            'position': 'after',
            'node': {'tag': 'field',
                     'attrs': {},
                     'field_description': {'type': 'binary',
                                           'field_description': 'New File',
                                           'name': 'x_studio_binary_field_WocAO',
                                           'model_name': 'res.partner'}}
        }

        self.edit_view(base_view, operations=[add_binary_op])

        add_widget_op = {
            'type': 'attributes',
            'target': {'tag': 'field',
                       'attrs': {'name': 'x_studio_binary_field_WocAO'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 2}]},
            'position': 'attributes',
            'node': {'tag': 'field',
                     'attrs': {'filename': 'x_studio_binary_field_WocAO_filename',
                               'name': 'x_studio_binary_field_WocAO',
                               'id': 'x_studio_binary_field_WocAO'},
                     'children': [],
                     'has_label': True},
            'new_attrs': {'widget': 'pdf_viewer', 'options': ''}
        }

        ops = [
            add_binary_op,
            add_widget_op
        ]
        self.edit_view(base_view, operations=ops)

        remove_binary_op = {
            'type': 'remove',
            'target': {'tag': 'field',
                       'attrs': {'name': 'x_studio_binary_field_WocAO'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 2}]},
        }
        self.edit_view(base_view, operations=ops + [remove_binary_op])
        # The filename field is still present in the view
        # this is not intentional rather, it is way easier to leave this invisible field there
        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
              <form>
                <field name="display_name"/>
                <field invisible="True" name="x_studio_binary_field_WocAO_filename"/>
              </form>
            """
        )

    def test_edit_view_options_attribute(self):
        op = {
            'type': 'attributes',
            'target': {
                'tag': 'field',
                'attrs': {'name': 'groups_id'},
                'xpath_info': [
                    {'tag': 'group', 'indice': 1},
                    {'tag': 'group', 'indice': 2},
                    {'tag': 'field', 'indice': 2}
                ],
                'subview_xpath': "//field[@name='user_ids']/form"
            },
            'position': 'attributes',
            'node': {
                'tag': 'field',
                'attrs': {
                    'name': 'groups_id',
                    'widget': 'many2many_tags',
                    'options': "{'color_field': 'color'}",
                },
                'children': [],
                'has_label': True
            },
            'new_attrs': {'options': '{"color_field":"color","no_create":true}'}
        }

        base_view = self.env['ir.ui.view'].create({
            'name': 'TestForm',
            'type': 'form',
            'model': 'res.partner',
            'arch': """
                    <form>
                        <sheet>
                            <field name="display_name"/>
                            <field name="user_ids">
                                <form>
                                    <sheet>
                                        <field name="groups_id" widget='many2many_tags' options="{'color_field': 'color'}"/>
                                    </sheet>
                                </form>
                            </field>
                        </sheet>
                    </form>"""
        })
        self.edit_view(base_view, operations=[op], model='res.users')

        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
                <form>
                    <sheet>
                        <field name="display_name"/>
                        <field name="user_ids">
                            <form>
                                <sheet>
                                    <field name="groups_id" widget="many2many_tags" options="{&quot;color_field&quot;: &quot;color&quot;, &quot;no_create&quot;: true}"/>
                                </sheet>
                            </form>
                        </field>
                    </sheet>
                </form>
            """
        )

    def test_edit_view_create_attribute_attribute(self):
        op = {
            'type': 'attributes',
            'target': {
                'tag': 'kanban',
                'attrs': {},
                'xpath_info': [
                    {'tag': 'kanban', 'indice': 1},
                ],
                'isSubviewAttr': True,
            },
            'position': 'attributes',
            'new_attrs': {'create': True}
        }

        base_view = self.env['ir.ui.view'].create({
            'name': 'TestKanban',
            'type': 'kanban',
            'model': 'res.partner',
            'arch': """
                <kanban>
                    <templates><t t-name="kanban-box" /></templates>
                </kanban>
            """
        })
        self.edit_view(base_view, operations=[op], model='res.users')

        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
                <kanban create="true">
                    <templates><t t-name="kanban-box" /></templates>
                </kanban>
            """
        )

    def test_edit_view_add_binary_field_inside_group(self):
        arch = """<form>
            <sheet>
                <notebook>
                    <page>
                        <group>
                            <group name="group_left" />
                            <group name="group_right" />
                        </group>
                    </page>
                </notebook>
            </sheet>
        </form>"""

        base_view = self.env['ir.ui.view'].create({
            'name': 'TestForm',
            'type': 'form',
            'model': 'res.partner',
            'arch': arch
        })

        operation = {
            'type': 'add',
            'target': {
                'tag': 'group',
                'attrs': {
                    'name': 'group_left'
                },
                'xpath_info': [
                    {'tag': 'form', 'indice': 1},
                    {'tag': 'sheet', 'indice': 1},
                    {'tag': 'notebook', 'indice': 1},
                    {'tag': 'page', 'indice': 1},
                    {'tag': 'group', 'indice': 1},
                    {'tag': 'group', 'indice': 1}
                ]
            },
            'position': 'inside',
            'node': {
                'tag': 'field',
                'attrs': {},
                'field_description': {
                    'type': 'binary',
                    'field_description': 'New File',
                    'name': 'x_studio_field_fDthx',
                    'model_name': 'res.partner'
                }

            }
        }

        self.edit_view(base_view, operations=[operation])

        expected_arch = """<form>
            <sheet>
                <notebook>
                    <page>
                        <group>
                            <group name="group_left">
                                <field filename="x_studio_field_fDthx_filename" name="x_studio_field_fDthx"/>
                                <field invisible="True" name="x_studio_field_fDthx_filename"/>
                            </group>
                            <group name="group_right"/>
                        </group>
                    </page>
                </notebook>
            </sheet>
        </form>"""

        self.assertViewArchEqual(base_view.get_combined_arch(), expected_arch)

    def test_edit_attribute_studio_groups(self):
        """ Tests the behavior of setting the attribute `studio_groups` on field view nodes having a `groups=` attribute
        A second goal is to test the behavior of a field node having a `groups=` attribute set on the node
        and another `groups=` on the field definition in the model.
        e.g.
        `code = fields.Text(string='Python Code', groups='base.group_system',`
        `<field name="code" groups="base.group_no_one"/>`
        For this above case, a temporary technical node is created during the view postprocessing,
        wrapping the `<field groups="..."` node,
        to simulate a AND between the two groups: you must have BOTH groups in order to see the given field node,
        and the technical node should not remain in the end.
        """
        # Ensure there is a group on the `code` field, as the goal of this test is to test the behavior
        # of a field having a group in the model definition in addition to another group on the field node in the view.
        self.assertEqual(self.env['ir.actions.server']._fields['code'].groups, 'base.group_system')
        view = self.env['ir.ui.view'].create({
            'name': 'foo',
            'type': 'tree',
            'model': 'ir.actions.server',
            'arch': """
                <tree>
                    <field name="name"/>
                    <field name="state" groups="base.group_no_one"/>
                    <field name="code" groups="base.group_no_one"/>
                </tree>"""
        })
        with self.debug_mode():
            arch = self.env['ir.actions.server'].with_context(studio=True).get_view(view.id)['arch']
            tree = etree.fromstring(arch)
            children = list(tree.iterdescendants())
            self.assertEqual(len(children), 3, 'The tree view must have only 3 descendants in total, the 3 fields')
            name, state, code = children
            self.assertFalse(name.get('studio_groups'))
            self.assertTrue(state.get('studio_groups'))
            self.assertTrue(code.get('studio_groups'))
            for node in (state, code):
                self.assertEqual(json.loads(node.get('studio_groups'))[0]['name'], 'Technical Features')

    def test_edit_field_present_in_multiple_views(self):
        """ a use case where the hack before this fix doesn't work.
        We try to edit a field that is present in two views, and studio
        must modify the field in the correct view and do not confuse it
        with the other one.
        """
        IrModelFields = self.env["ir.model.fields"].with_context(studio=True)
        source_model = self.env["ir.model"].search([("model", "=", "res.partner")])
        destination_model = self.env["ir.model"].search(
            [("model", "=", "res.currency")]
        )
        IrModelFields.create(
            {
                "ttype": "many2many",
                "model_id": source_model.id,
                "relation": destination_model.model,
                "name": "x_test_field_x",
                "relation_table": IrModelFields._get_next_relation(
                    source_model.model, destination_model.model
                ),
            }
        )
        arch = """ <form>
            <field name="user_ids">
                <form>
                    <field name="x_test_field_x"/>
                </form>
                <tree>
                    <field name="x_test_field_x"/>
                </tree>
            </field>
        </form>"""

        base_view = self.env['ir.ui.view'].create({
            'name': 'TestForm',
            'type': 'form',
            'model': 'res.partner',
            'arch': arch
        })

        operation = {
            'type': 'attributes',
            'target': {
                'tag': 'field',
                    'attrs': {
                        'name': 'x_test_field_x'
                    },
                    'xpath_info': [
                        {'tag': 'tree', 'indice': 1},
                        {'tag': 'field', 'indice': 1}
                    ],
                    'subview_xpath': "//field[@name='user_ids']/tree"
                },
                'position': 'attributes',
                'node': {
                    'tag': 'field',
                    'attrs': {
                        'name': 'x_test_field_x',
                        'id': 'x_test_field_x'
                    },
                },
                'new_attrs': {
                    'options': "{\"no_create\": true}"
                }
            }

        self.edit_view(base_view, operations=[operation])

        expected_arch = """ <form>
            <field name="user_ids">
                <form>
                    <field name="x_test_field_x"/>
                </form>
                <tree>
                    <field name="x_test_field_x" options="{&quot;no_create&quot;: true}"/>
                </tree>
            </field>
        </form>"""
        self.assertViewArchEqual(base_view.get_combined_arch(), expected_arch)

    def test_edit_attribute_studio_groups_tree_column_invisible(self):
        for view_type, arch, expected_modifiers in [
            ('tree', """
                <tree>
                    <field name="name" groups="base.group_no_one"/>
                </tree>
            """, {'column_invisible': 'True', 'invisible': None}),
            ('tree', """
                <tree>
                    <header>
                        <button name="name" groups="base.group_no_one"/>
                    </header>
                </tree>
            """, {'invisible': 'True', 'column_invisible': None}),
            ('form', """
                <form>
                    <field name="child_ids">
                        <tree>
                            <field name="name" groups="base.group_no_one"/>
                        </tree>
                    </field>
                </form>
            """, {'column_invisible': 'True', 'invisible': None}),
            ('tree', """
                <tree>
                    <field name="child_ids">
                        <form>
                            <field name="name" groups="base.group_no_one"/>
                        </form>
                    </field>
                </tree>
            """, {'invisible': 'True', 'column_invisible': None}),
        ]:
            view = self.env['ir.ui.view'].create({
                'name': 'foo',
                'type': view_type,
                'model': 'res.partner',
                'arch': arch,
            })
            arch = self.env['res.partner'].with_context(studio=True).get_view(view.id)['arch']
            tree = etree.fromstring(arch)
            node = tree.xpath('//*[@name="name"]')[0]
            for modifier, value in expected_modifiers.items():
                self.assertEqual(node.get(modifier), value)

    def test_get_view_t_groups(self):
        """Tests the behavior of <t groups="..."></t> blocks with Studio."""
        for view_type, arch, expected_modifiers in [
            # The user has the group of the `<t>` node, the `<t>` node **must remain**, and be visible.
            ('form', """
                <form>
                    <t groups="base.group_user">
                        <field name="name"/>
                    </t>
                </form>
            """, {'invisible': None}),
            # The user doesn't have the group of the `<t>` node, the `<t>` node **must remain**, and be invisible.
            ('form', """
                <form>
                    <t groups="base.group_no_one">
                        <field name="name"/>
                    </t>
                </form>
            """, {'invisible': 'True'}),
        ]:
            view = self.env['ir.ui.view'].create({
                'name': 'foo',
                'type': view_type,
                'model': 'res.partner',
                'arch': arch,
            })
            arch = self.env['res.partner'].with_context(studio=True).get_view(view.id)['arch']
            tree = etree.fromstring(arch)
            self.assertTrue(tree.xpath('//t'))
            node = tree.xpath('//t')[0]
            for modifier, value in expected_modifiers.items():
                self.assertEqual(node.get(modifier), value)

    def test_open_users_form_with_studio(self):
        """Tests the res.users form view can be loaded with Studio.

        The res.users form is an edge case, because it uses fake fields in its view, which do not exist in the model.
        Make sure the Studio overrides regarding the loading of the views, including the postprocessing,
        are able to handle these non-existing fields.
        """
        arch = self.env['res.users'].with_context(studio=True).get_view(self.env.ref('base.view_users_form').id)['arch']
        self.assertTrue(arch)

    def test_add_many2one_with_custom_rec_name(self):
        base_view = self.env['ir.ui.view'].create({
            'name': 'TestForm',
            'type': 'form',
            'model': 'res.partner',
            'arch': """
                    <form>
                        <field name="display_name" />
                    </form>"""
        })

        relation_id = self.env['ir.model'].search([["model", "=", "res.partner.bank"]]).id

        add_many2one_field_op = {
            "type": "add",
            "target": {
                "tag": "field",
                "attrs": {"name": "display_name"},
                "xpath_info": [
                    {"tag": "form", "indice": 1},
                    {"tag": "field", "indice": 1},
                ],
            },
            "position": "after",
            "node": {
                "tag": "field",
                "attrs": {},
                "field_description": {
                    "type": "many2one",
                    "field_description": "ddd",
                    "special": False,
                    "name": "x_studio_many2one_field_sNT7g",
                    "model_name": "res.partner",
                    "relation_id": relation_id,
                },
            },
        }

        self.edit_view(base_view, operations=[add_many2one_field_op])
        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
              <form>
                <field name="display_name" />
                <field name="x_studio_many2one_field_sNT7g" options="{'create_name_field': 'acc_number'}"/>
              </form>
            """
        )
