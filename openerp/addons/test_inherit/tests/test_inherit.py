# -*- coding: utf-8 -*-
from openerp.tests import common

class test_inherits(common.TransactionCase):

    def test_access_from_child_to_parent_model(self):
        """ check whether added field in model is accessible from children models (_inherits) """
        # This test checks if the new added column of a parent model
        # is accessible from the child model. This test has been written
        # to verify the purpose of the inheritance computing of the class
        # in the openerp.osv.orm._build_model.
        mother = self.env['test.inherit.mother']
        daughter = self.env['test.inherit.daughter']

        self.assertIn('field_in_mother', mother._fields)
        self.assertIn('field_in_mother', daughter._fields)

    def test_field_extension(self):
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
        self.assertEqual(field.default(mother), "Baz")
        self.assertEqual(daughter._defaults.get('name'), "Baz")
        self.assertEqual(daughter.default_get(['name']), {'name': "Baz"})

        # the field daughter.template_id should have
        # comodel_name='test.inherit.mother', string='Template', required=True
        field = daughter._fields['template_id']
        self.assertEqual(field.comodel_name, 'test.inherit.mother')
        self.assertEqual(field.string, "Template")
        self.assertTrue(field.required)

    def test_depends_extension(self):
        """ check that @depends on overridden compute methods extends dependencies """
        mother = self.env['test.inherit.mother']
        field = mother._fields['surname']

        # the field dependencies are added
        self.assertItemsEqual(field.depends, ['name', 'field_in_mother'])

    def test_selection_extension(self):
        """ check that attribute selection_add=... extends selection on fields. """
        mother = self.env['test.inherit.mother']

        # the extra values are added, both in the field and the column
        self.assertEqual(mother._fields['state'].selection,
                         [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')])
        self.assertEqual(mother._columns['state'].selection,
                         [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')])


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
