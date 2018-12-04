# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestBasicAssumptions(common.TransactionCase):

    def setUp(self):
        super(TestBasicAssumptions, self).setUp()

        self.Model = self.env['test_complete_field.model']

    def test_allowed_fields_types(self):
        """ Only m2o fields can be completed at this point """
        # executions with fault (not support these fields)
        for field in ['boolean_field', 'integer_field', 'float_field', 'char_field', 'selection_field']:
            with self.assertRaises(ValueError):
                self.Model.complete_field(field, 'thing')
        # executions with no fault
        result = self.Model.complete_field('m2o_field', 'thing')
        self.assertTrue(len(result) >= 0, 'Only m2o fields are supported!')
