# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestUniqueCompletion(common.TransactionCase):

    def test_redundancies(self):
        SubModel = self.env['test_complete_field.sub_model'].create({
            'name': 'Feature request',
            'tag': 42,
        })
        ParentModel = self.env['test_complete_field.model']
        for i in range(42):
            ParentModel.create({'m2o_field': SubModel.id})

        results = ParentModel.complete_field('m2o_field', '')
        self.assertEqual(results, [(SubModel.id, 'Feature request')])

    def test_sufficient_results(self):
        """ Limiting should be performed after uniquification, not before """
        SubModel = self.env['test_complete_field.sub_model']
        record1 = SubModel.create({'name': 'Theatre', 'tag': 1})
        record2 = SubModel.create({'name': 'Foyer Royal', 'tag': 2})

        ParentModel = self.env['test_complete_field.model']
        for i in range(42):
            # pad with a bunch of identical objects
            ParentModel.create({'m2o_field': record1.id})
        ParentModel.create({'m2o_field': record2.id})

        results = ParentModel.complete_field('m2o_field', '')
        self.assertEqual(results, [(record1.id, 'Theatre'), (record2.id, 'Foyer Royal')])
