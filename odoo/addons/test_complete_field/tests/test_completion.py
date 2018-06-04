# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestBasicCompletion(common.TransactionCase):

    def setUp(self):
        super(TestBasicCompletion, self).setUp()

        self.ParentModel = self.env['test_complete_field.model']
        self.SubModel = self.env['test_complete_field.sub_model']

        items = [
            ('Product', 1),
            ('Software', 1),
            ('Services', 2),
            ('Information', 3),
            ('Design', 4),
            ('Training', 4),
            ('Consulting', 4),
            ('Other', 4),
            ('NeedAssistance', 5),
            ('Spam', 5),
            ('Created by Partner', 5),
            ('Usability', 6),
            ('Experiment', 7),
        ]

        for item in items:
            record = self.SubModel.create({
                'name': item[0],
                'tag': item[1]
            })
            if item[1] > 2:
                self.ParentModel.create({
                    'm2o_field': record.id,
                    'boolean_field': bool(item[1] % 2),
                })

    def convert_tuple_to_list(self, results):
        return [res[1] for res in results]

    def test_get_all(self):
        # get limited record, which is linked to the patent model (default limit is 8)
        results = self.ParentModel.complete_field('m2o_field', '')
        self.assertEqual(len(results), 9, "by default completion should provide 9 items tops")

        # get unlimited record, which is linked to the patent model
        results = self.ParentModel.complete_field('m2o_field', '', limit=None)
        self.assertEqual(len(results), 10, "should only return m2os linked to a parent record")

    def test_complete_value(self):
        results = self.ParentModel.complete_field('m2o_field', 'Tra')
        self.assertEqual(self.convert_tuple_to_list(results), ['Training'])

    def test_filter_based_on_field_doamin(self):
        results = self.ParentModel.complete_field('m2o_field', '', field_domain=[('tag', '=', 5)])
        self.assertEqual(self.convert_tuple_to_list(results), ['NeedAssistance', 'Spam', 'Created by Partner'])

    def test_filter_based_on_parent_doamin(self):
        results = self.ParentModel.complete_field('m2o_field', '', parent_domain=[('boolean_field', '=', True)])
        self.assertEqual(self.convert_tuple_to_list(results), ['Information', 'NeedAssistance', 'Spam', 'Created by Partner', 'Experiment'])

    def test_filter_all_the_things(self):
        results = self.ParentModel.complete_field('m2o_field', 'p', field_domain=[('tag', '=', 5)], parent_domain=[('boolean_field', '=', True)])
        self.assertEqual(self.convert_tuple_to_list(results), ['Spam', 'Created by Partner'])

    def test_compute_field(self):
        results = self.ParentModel.complete_field('compute_m2o_field', '')
        self.assertEqual(len(results), 5, "by default completion should provide 5 items tops")

        results = self.ParentModel.complete_field('compute_m2o_field', 'Exp')
        self.assertEqual(self.convert_tuple_to_list(results), ['Experiment'])

        results = self.ParentModel.complete_field('compute_m2o_field', '', field_domain=[('tag', '=', 5)])
        self.assertEqual(self.convert_tuple_to_list(results), ['NeedAssistance', 'Spam', 'Created by Partner'])

        results = self.ParentModel.complete_field('compute_m2o_field', '', parent_domain=[('boolean_field', '=', True)])
        self.assertEqual(self.convert_tuple_to_list(results), ['Information', 'NeedAssistance', 'Spam', 'Created by Partner', 'Experiment'])

        results = self.ParentModel.complete_field('compute_m2o_field', 'p', field_domain=[('tag', '=', 5)], parent_domain=[('boolean_field', '=', True)])
        self.assertEqual(self.convert_tuple_to_list(results), ['Spam', 'Created by Partner'])
