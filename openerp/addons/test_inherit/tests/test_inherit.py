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
        daugther = self.env['test.inherit.daughter']

        self.assertIn('field_in_mother', mother._fields)
        self.assertIn('field_in_mother', daugther._fields)

    def test_field_extension(self):
        """ check the extension of a field in an inherited model """
        # the field mother.name should inherit required=True, and have a default
        # value
        mother = self.env['test.inherit.mother']
        field = mother._fields['name']
        self.assertTrue(field.required)
        self.assertEqual(field.default, 'Unknown')

        # the field daugther.template_id should inherit
        # model_name='test.inherit.mother', string='Template', required=True
        daugther = self.env['test.inherit.daughter']
        field = daugther._fields['template_id']
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
        field = mother._fields['state']

        # the extra values are added
        self.assertEqual(field.selection, [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')])


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
