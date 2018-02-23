# -*- coding: utf-8 -*-
from openerp.tests import common

class test_inherits(common.TransactionCase):

    def test_00_inherits(self):
        """ Check that a many2one field with delegate=True adds an entry in _inherits """
        daughter = self.env['test.inherit.daughter']

        self.assertEqual(daughter._inherits, {'test.inherit.mother': 'template_id'})

    def test_10_access_from_child_to_parent_model(self):
        """ check whether added field in model is accessible from children models (_inherits) """
        # This test checks if the new added column of a parent model
        # is accessible from the child model. This test has been written
        # to verify the purpose of the inheritance computing of the class
        # in the openerp.osv.orm._build_model.
        mother = self.env['test.inherit.mother']
        daughter = self.env['test.inherit.daughter']

        self.assertIn('field_in_mother', mother._fields)
        self.assertIn('field_in_mother', daughter._fields)

    def test_20_field_extension(self):
        """ check the extension of a field in an inherited model """
        mother = self.env['test.inherit.mother']
        daughter = self.env['test.inherit.daughter']

        # the field mother.name must have required=True and "Bar" as default
        field = mother._fields['name']
        self.assertTrue(field.required)
        self.assertEqual(field.default(mother), "Bar")
        self.assertEqual(mother._defaults.get('name'), "Bar")
        self.assertEqual(mother.default_get(['name']), {'name': "Bar"})

        # the field daughter.name must have required=False and "Baz" as default
        field = daughter._fields['name']
        self.assertFalse(field.required)
        self.assertEqual(field.default(daughter), "Baz")
        self.assertEqual(daughter._defaults.get('name'), "Baz")
        self.assertEqual(daughter.default_get(['name']), {'name': "Baz"})

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
        self.assertItemsEqual(field.depends, ['name', 'field_in_mother'])

    def test_40_selection_extension(self):
        """ check that attribute selection_add=... extends selection on fields. """
        mother = self.env['test.inherit.mother']

        # the extra values are added, both in the field and the column
        self.assertEqual(mother._fields['state'].selection,
                         [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')])
        self.assertEqual(mother._columns['state'].selection,
                         [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')])

    def test_50_search_one2many(self):
        """ check search on one2many field based on inherited many2one field. """
        # create a daughter record attached to partner Demo
        partner_demo = self.env.ref('base.partner_demo')
        daughter = self.env['test.inherit.daughter'].create({'partner_id': partner_demo.id})
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

    def test_override_with_function_field(self):
        """ test overriding a property field by a function field """
        record = self.env['test.inherit.property'].create({'name': "Stuff"})
        # record.property_foo is not a property field
        self.assertEqual(record.property_foo, 42)
        self.assertFalse(type(record).property_foo.company_dependent)

    def test_override_with_computed_field(self):
        """ test overriding a property field by a computed field """
        record = self.env['test.inherit.property'].create({'name': "Stuff"})
        # record.property_bar is not a property field
        self.assertEqual(record.property_bar, 42)
        self.assertFalse(type(record).property_bar.company_dependent)
