# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestViews(TransactionCase):

    def setUp(self):
        super().setUp()
        View = self.env['ir.ui.view']
        self.first_view = View.create({
            'name': 'Test View 1',
            'type': 'qweb',
            'arch': '<div>Hello World</div>',
            'key': 'html_editor.test_first_view',
        })
        self.second_view = View.create({
            'name': 'Test View 2',
            'type': 'qweb',
            'arch': '<div><t t-call="html_editor.test_first_view"/></div>',
            'key': 'html_editor.test_second_view',
        })

    def test_infinite_inherit_loop(self):
        # Creates an infinite loop: A t-call B and A inherit from B
        View = self.env['ir.ui.view']

        self.second_view.write({
            'inherit_id': self.first_view.id,
        })
        # Test for RecursionError: maximum recursion depth exceeded in this function
        View._views_get(self.first_view)

    def test_oe_structure_as_inherited_view(self):
        View = self.env['ir.ui.view']

        base = View.create({
            'name': 'Test View oe_structure',
            'type': 'qweb',
            'arch': """<xpath expr='//t[@t-call="html_editor.test_first_view"]' position='after'>
                        <div class="oe_structure" id='oe_structure_test_view_oe_structure'/>
                    </xpath>""",
            'key': 'html_editor.oe_structure_view',
            'inherit_id': self.second_view.id
        })

        # check view mode
        self.assertEqual(base.mode, 'extension')

        # update content of the oe_structure
        value = '''<div class="oe_structure" id="oe_structure_test_view_oe_structure" data-oe-id="%s"
                         data-oe-xpath="/div" data-oe-model="ir.ui.view" data-oe-field="arch">
                        <p>Hello World!</p>
                   </div>''' % base.id

        base.save(value=value, xpath='/xpath/div')

        self.assertEqual(len(base.inherit_children_ids), 1)
        self.assertEqual(base.inherit_children_ids.mode, 'extension')
        self.assertIn(
            '<p>Hello World!</p>',
            base.inherit_children_ids.get_combined_arch(),
        )

    def test_oe_structure_keeps_translations(self):
        self.env['res.lang']._activate_lang('fr_FR')
        view = self.env['ir.ui.view'].create({
            'name': 'Test View translated oe_structure',
            'type': 'qweb',
            'arch': '<div><div class="oe_structure" id="oe_structure_test_translated"><p>Hello World</p></div></div>',
            'key': 'html_editor.test_translated_oe_structure',
        })
        view.update_field_translations('arch_db', {'fr_FR': {'Hello World': 'Bonjour le monde'}})

        # the first save of the oe_structure moves it into its own view
        value = '''<div class="oe_structure" id="oe_structure_test_translated" data-oe-id="%s"
                         data-oe-xpath="/div/div" data-oe-model="ir.ui.view" data-oe-field="arch">
                        <p>Hello World</p>
                        <p>New paragraph</p>
                   </div>''' % view.id
        view.save(value=value, xpath='/div/div')

        oe_structure_view = view.inherit_children_ids
        self.assertEqual(len(oe_structure_view), 1)
        arch_fr = oe_structure_view.with_context(lang='fr_FR').arch_db
        self.assertIn('<p>Bonjour le monde</p>', arch_fr)
        self.assertIn('<p>New paragraph</p>', arch_fr)

    def test_find_available_name(self):
        View = self.env['ir.ui.view']
        used_names = ['Unrelated name']
        initial_name = "Test name"
        name = View._find_available_name(initial_name, used_names)
        self.assertEqual(initial_name, name)
        used_names.append(name)
        name = View._find_available_name(initial_name, used_names)
        self.assertEqual('Test name (2)', name)
        used_names.append(name)
        name = View._find_available_name(initial_name, used_names)
        self.assertEqual('Test name (3)', name)
