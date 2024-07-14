# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import test_common

class TestDeduplication(test_common.TestCommon):
    def test_deduplication_exact(self):
        self._create_rule('x_name', 'exact')

        self._create_record('x_dm_test_model', x_name='toto')
        self._create_record('x_dm_test_model', x_name='titi')
        self._create_record('x_dm_test_model', x_name='tutu')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 0, '0 record should have been found')

        self._create_record('x_dm_test_model', x_name='toto')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 2, '2 records should have been found')

    def test_deduplication_accent(self):
        self._create_rule('x_name', 'accent')

        self._create_record('x_dm_test_model', x_name='toto')
        self._create_record('x_dm_test_model', x_name='titi')
        self._create_record('x_dm_test_model', x_name='tutu')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 0, '0 record should have been found')

        self._create_record('x_dm_test_model', x_name='tùtù')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 2, '2 records should have been found')

    def test_deduplication_multiple(self):
        self._create_rule('x_name', 'exact')
        self._create_rule('x_email', 'exact')

        self._create_record('x_dm_test_model', x_name='toto', x_email='toto@example.com')
        self._create_record('x_dm_test_model', x_name='bob', x_email='bob@example.com')
        self._create_record('x_dm_test_model', x_name='alfred', x_email='alfred@example.com')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 0, '0 record should have been found')

        self._create_record('x_dm_test_model', x_name='toto', x_email='real_toto@example.com')
        self._create_record('x_dm_test_model', x_name='titi', x_email='bob@example.com')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 4, '4 records should have been found')

        self.DMGroup.search([('model_id', '=', self.MyModel.id)]).unlink()

        self._create_record('x_dm_test_model', x_name='titi', x_email='real_toto@example.com')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 5, '5 records should have been found')
        self.assertEqual(self.DMGroup.search_count([('model_id', '=', self.MyModel.id)]), 1, '1 group should have been created')

        self.DMGroup.search([('model_id', '=', self.MyModel.id)]).unlink()

        self._create_record('x_dm_test_model', x_name='robert', x_email='alfred@example.com')
        self._create_record('x_dm_test_model', x_name='jacky', x_email='jacky@example.com')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 7, '7 records should have been found')
        self.assertEqual(self.DMGroup.search_count([('model_id', '=', self.MyModel.id)]), 2, '2 groups should have been created')

    def test_deduplication_threshold(self):
        self._create_rule('x_name', 'exact')
        self._create_rule('x_email', 'exact')

        self._create_record('x_dm_test_model', x_name='toto', x_email='toto@example.com')
        self._create_record('x_dm_test_model', x_name='toto', x_email='real_toto@example.com')

        self.assertEqual(self.MyModel.create_threshold, 0, 'Suggestion Threshold shoud be at 0')

        # Ensure that groups added both records
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 2, '2 record should have been found')

        # Ensure that groups are removed after suggested threshold is changed to above similarity
        self.MyModel.create_threshold = 70
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 0, '0 record should have been found')

        # Ensure that groups are not updated after suggested threshold is changed to bellow similarity
        self.MyModel.create_threshold = 40
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 0, '0 record should have been found')

        # Ensure that groups are updated after find_duplicates
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 2, '2 record should have been found')

    def test_record_references(self):
        self._create_rule('x_name', 'exact')

        rec = self._create_record('x_dm_test_model', x_name='toto')
        self._create_record('x_dm_test_model_ref', x_name='ref toto', x_test_id=rec.id)
        self._create_record('x_dm_test_model', x_name='toto')
        self.MyModel.find_duplicates()

        records = self.env['data_merge.record'].search([('res_id', '=', rec.id), ('model_id', '=', self.MyModel.id)])

        self.assertEqual(len(records), 1, "Should have found 1 record")

        ref = records[0]._get_references().get(records[0].id)

        self.assertEqual(len(ref), 1, "The record should have 1 reference")
        self.assertEqual(ref[0][0], 1, "The record should have 1 referencing record")
        self.assertEqual(ref[0][1], 'Test Model Ref', "Model should be Test Model Ref")

    def test_record_active(self):
        self._create_rule('x_name', 'exact')
        rec = self._create_record('x_dm_test_model', x_name='toto')
        self._create_record('x_dm_test_model', x_name='toto')
        self.MyModel.find_duplicates()

        records = self.env['data_merge.record'].search([('res_id', '=', rec.id), ('model_id', '=', self.MyModel.id)])
        self.assertEqual(len(records), 1, "Should have found 1 record")

        record = records[0]
        self.assertEqual(record._original_records(), rec, "Both records should be equal")
        self.assertTrue(record.active, "The record should be active")
        self.assertFalse(record.is_discarded, "Should not be discarded")
        self.assertFalse(record.is_deleted, "Should not be deleted")

        rec.unlink()
        record._compute_active()
        self.assertFalse(record.active, "Record should be inactive")
        self.assertTrue(record.is_deleted, "The record should be deleted")

    def test_multi_model(self):
        self._create_rule('x_name', 'exact', model_name='x_dm_test_model')
        self._create_rule('x_name', 'exact', model_name='x_dm_test_model2')

        self._create_record('x_dm_test_model', x_name='abc')
        self._create_record('x_dm_test_model', x_name='abc')

        self._create_record('x_dm_test_model2', x_name='abc')
        self._create_record('x_dm_test_model2', x_name='abc')
        self._create_record('x_dm_test_model2', x_name='abc')

        self.MyModel.find_duplicates()
        self.MyModel2.find_duplicates()

        records_wrong_company = self.env['data_merge.record'].search([('model_id', '=', self.MyModel.id), ('company_id', '=', 1)])
        self.assertEqual(len(records_wrong_company), 0, "Should have found 0 records")

        records_model1 = self.env['data_merge.record'].search([('model_id', '=', self.MyModel.id)])
        records_model2 = self.env['data_merge.record'].search([('model_id', '=', self.MyModel2.id)])
        self.assertEqual(len(records_model1), 2, "Should have found 2 records")
        self.assertEqual(len(records_model2), 3, "Should have found 3 records")

        self.assertEqual(records_model1[0].name, 'abc', "Should have read name abc")
        self.assertEqual(records_model2[0].name, 'abc', "Should have read name abc")

    def test_search_company_id_data_merge_record(self):
        dmm = self.DMModel.with_user(self.env.ref('base.user_admin')).create({
            'name': 'Test new',
            'res_model_id': self.DMTestModel.id,
        })
        dmm.modified(['records_to_merge_count'])
        self.assertEqual(dmm.records_to_merge_count, 0, "records_to_merge_count is calulated without error")
