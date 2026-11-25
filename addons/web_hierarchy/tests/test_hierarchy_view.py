# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.addons.base.tests.test_ir_ui_view import ViewCase

CARD = """
    <templates>
        <t t-name="card"><field name="name"/></t>
    </templates>
"""


class TestHierarchyView(ViewCase):

    def assertValidHierarchy(self, arch):
        return self.assertValid(arch, model='res.partner')

    def assertInvalidHierarchy(self, arch, expected_message):
        self.assertInvalid(arch, expected_message, model='res.partner')

    def test_valid(self):
        view = self.assertValidHierarchy(f'<hierarchy child_field="child_ids">{CARD}</hierarchy>')
        result = self.env['res.partner'].get_views([(view.id, 'hierarchy')])
        fields = result['models']['res.partner']['fields']
        self.assertIn('child_ids', fields)
        self.assertIn('parent_id', fields, "the parent field is deduced from the child field")
        arch = etree.fromstring(result['views']['hierarchy']['arch'])
        self.assertEqual(
            {node.get('name') for node in arch.xpath('/hierarchy/field')},
            {'child_ids', 'parent_id'},
        )

    def test_card_id(self):
        card_view = self.View.create({
            'name': 'partner card',
            'model': 'res.partner',
            'type': 'card',
            'arch': f'<card>{CARD}</card>',
        })
        view = self.assertValidHierarchy(f'<hierarchy child_field="child_ids" card_id="{card_view.id}"/>')
        result = self.env['res.partner'].get_views([(view.id, 'hierarchy')])
        arch = etree.fromstring(result['views']['hierarchy']['arch'])
        self.assertEqual(len(arch.xpath("/hierarchy/card/templates/t[@t-name='card']")), 1)

    def test_invalid_card_id(self):
        self.assertInvalidHierarchy(
            '<hierarchy child_field="child_ids" card_id="partner_card"/>',
            "Invalid card_id 'partner_card' in hierarchy view, it must be a view id",
        )

    def test_no_card(self):
        self.assertInvalidHierarchy(
            '<hierarchy child_field="child_ids"/>',
            "Hierarchy view must have a card_id attribute or a templates tag",
        )

    def test_two_templates(self):
        self.assertInvalidHierarchy(
            f'<hierarchy child_field="child_ids">{CARD}{CARD}</hierarchy>',
            "Hierarchy view can contain only one templates tag",
        )

    def test_invalid_child_node(self):
        self.assertInvalidHierarchy(
            f'<hierarchy child_field="child_ids"><div/>{CARD}</hierarchy>',
            "Hierarchy child can only be field or template, got div",
        )

    def test_no_child_field(self):
        self.assertInvalidHierarchy(
            f'<hierarchy>{CARD}</hierarchy>',
            "Hierarchy view must have a child_field attribute",
        )

    def test_invalid_child_field(self):
        for child_field_name, expected_message in [
            ('unknown_field', "Field 'unknown_field' set as child_field does not exist on model 'res.partner'"),
            ('category_id', "Field 'category_id' set as child_field must be a one2many field"),
            ('bank_ids', "Field 'bank_ids' set as child_field must target the model of the view 'res.partner'"),
        ]:
            with self.subTest(child_field_name=child_field_name):
                self.assertInvalidHierarchy(
                    f'<hierarchy child_field="{child_field_name}">{CARD}</hierarchy>',
                    expected_message,
                )

    def test_invalid_attribute(self):
        self.assertInvalidHierarchy(
            f'<hierarchy child_field="child_ids" parent_field="parent_id">{CARD}</hierarchy>',
            "Invalid attributes (parent_field) in hierarchy view.",
        )
