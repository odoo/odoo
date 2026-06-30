# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests import common
from ..models.mother_inherit_4 import TestInheritMother


class test_inherits(common.TransactionCase):

    def test_10_access_from_child_to_parent_model(self):
        """ check whether added field in model is accessible from children models (_inherits) """
        # This test checks if the new added column of a parent model
        # is accessible from the child model. This test has been written
        # to verify the purpose of the inheritance computing of the class
        # in the openerp.osv.orm._build_model.
        mother = self.env['test.inherit.mother']
        daughter = self.env['test_inherit_daughter']

        self.assertIn('field_in_mother', mother._fields)
        self.assertIn('field_in_mother', daughter._fields)

    def test_20_field_extension(self):
        """ check the extension of a field in an inherited model """
        mother = self.env['test.inherit.mother']
        daughter = self.env['test_inherit_daughter']

        # the field mother.name must have required=True and "Bar" as default
        field = mother._fields['name']
        self.assertTrue(field.required)
        self.assertEqual(field.default(mother), "Bar")
        self.assertEqual(mother.default_get(['name']), {'name': "Bar"})

        # the field daughter.name must have required=False and "Baz" as default
        field = daughter._fields['name']
        self.assertFalse(field.required)
        self.assertEqual(field.default(daughter), "Baz")
        self.assertEqual(daughter.default_get(['name']), {'name': "Baz"})

        # the field mother.state must have no default value
        field = mother._fields['state']
        self.assertFalse(field.default)
        self.assertEqual(mother.default_get(['state']), {})

        # the field daughter.template_id should have
        # comodel_name='test.inherit.mother', string='Template', required=True
        field = daughter._fields['template_id']
        self.assertEqual(field.comodel_name, 'test.inherit.mother')
        self.assertEqual(field.string, "Template")
        self.assertTrue(field.required)

    def test_30_depends_extension(self):
        """ check that @depends on overridden compute methods extends dependencies """
        mother = self.env['test.inherit.mother']
        field = mother._fields['surname']

        # the field dependencies are added
        self.assertItemsEqual(self.registry.field_depends[field], ['name', 'field_in_mother'])

    def test_40_selection_extension(self):
        """ check that attribute selection_add=... extends selection on fields. """
        mother = self.env['test.inherit.mother']

        # the extra values are added, both in the field and the column
        self.assertEqual(mother._fields['state'].selection,
                         [('a', 'A'), ('d', 'D'), ('b', 'B'), ('c', 'C'), ('e', 'E')])

    def test_41_selection_extension(self):
        """ check that attribute selection_add=... extends selection on fields. """
        model = self.env['test_orm.selection']
        field = model._fields['other']
        self.assertIsInstance(field.selection, str)
        self.assertEqual(field._description_selection(self.env), [('baz', 'Baz')])

    def test_51_define_model_inherit(self):
        model = self.env['test_inherit_parent']
        self.assertEqual(bool(model._fields['foo']), True)

    def test_60_inherit_with_python(self):
        self.assertEqual(self.env['test.inherit.mother'].foo(), 42)
        self.assertEqual(self.env[TestInheritMother._name].foo(), 42)
        self.assertEqual(self.env['test.inherit.mother'].browse(1).surname, 'Mother A')


class test_inherits_demo(TransactionCaseWithUserDemo):

    def test_50_search_one2many(self):
        """ check search on one2many field based on inherited many2one field. """
        # create a daughter record attached to partner Demo
        partner_demo = self.partner_demo
        daughter = self.env['test_inherit_daughter'].create({'partner_id': partner_demo.id})
        self.assertEqual(daughter.partner_id, partner_demo)
        self.assertIn(daughter, partner_demo.daughter_ids)

        # search the partner from the daughter record
        partners = self.env['res.partner'].search([('daughter_ids', 'like', 'not existing daugther')])
        self.assertFalse(partners)
        partners = self.env['res.partner'].search([('daughter_ids', 'not like', 'not existing daugther')])
        self.assertIn(partner_demo, partners)
        partners = self.env['res.partner'].search([('daughter_ids', '!=', False)])
        self.assertIn(partner_demo, partners)
        partners = self.env['res.partner'].search([('daughter_ids', 'in', daughter.ids)])
        self.assertIn(partner_demo, partners)


class test_override_property(common.TransactionCase):

    def test_override_with_normal_field(self):
        """ test overriding a property field by a function field """
        record = self.env['test_inherit_property'].create({'name': "Stuff"})
        # record.property_foo is not a property field
        self.assertFalse(record.property_foo)
        self.assertFalse(type(record).property_foo.company_dependent)
        self.assertTrue(type(record).property_foo.store)

    def test_override_with_computed_field(self):
        """ test overriding a property field by a computed field """
        record = self.env['test_inherit_property'].create({'name': "Stuff"})
        # record.property_bar is not a property field
        self.assertEqual(record.property_bar, 42)
        self.assertFalse(type(record).property_bar.company_dependent)


class TestInherit(common.TransactionCase):
    def test_ir_model_inherit(self):
        imi = self.env['ir.model.inherit'].search(
            [('model_id.model', '=', 'test_inherit_child')]
        )
        self.assertEqual(len(imi), 1)
        self.assertEqual(imi.parent_id.model, 'test_inherit_parent')
        self.assertFalse(imi.parent_field_id)

    def test_extend_parent(self):
        """ test whether a model extension is visible in its children models. """
        parent = self.env['test_inherit_parent']
        child = self.env['test_inherit_child']

        # check fields
        self.assertIn('foo', parent.fields_get())
        self.assertNotIn('bar', parent.fields_get())
        self.assertIn('foo', child.fields_get())
        self.assertIn('bar', child.fields_get())

        # check method overriding
        self.assertEqual(parent.stuff(), 'P1P2')
        self.assertEqual(child.stuff(), 'P1P2C1')

        # check inferred model attributes
        self.assertEqual(parent._table, 'test_inherit_parent')
        self.assertEqual(child._table, 'test_inherit_child')
        self.assertEqual(len(parent._table_objects), 1)
        self.assertEqual(len(child._table_objects), 1)

        # check properties memoized on model
        self.assertEqual(len(parent._constraint_methods), 1)
        self.assertEqual(len(child._constraint_methods), 1)


class TestXMLIDS(common.TransactionCase):
    def test_xml_ids(self):
        """ check XML ids of selection fields. """
        field = self.env['test_orm.selection']._fields['state']
        self.assertEqual(field.selection, [('foo', 'Foo'), ('bar', 'Bar'), ('baz', 'Baz')])

        ir_field = self.env['ir.model.fields']._get('test_orm.selection', 'state')
        xml_ids = ir_field._get_external_ids()
        self.assertCountEqual(xml_ids.get(ir_field.id), [
            'test_orm.field_test_orm_selection__state',
            'test_inherit.field_test_orm_selection__state',
        ])

        foo, bar, baz = ir_field.selection_ids
        xml_ids = (foo + bar + baz)._get_external_ids()
        self.assertCountEqual(xml_ids.get(foo.id), [
            'test_orm.selection__test_orm_selection__state__foo',
        ])
        self.assertCountEqual(xml_ids.get(bar.id), [
            'test_orm.selection__test_orm_selection__state__bar',
            'test_inherit.selection__test_orm_selection__state__bar',
        ])
        self.assertCountEqual(xml_ids.get(baz.id), [
            'test_inherit.selection__test_orm_selection__state__baz',
        ])
