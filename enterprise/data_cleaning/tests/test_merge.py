# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from unittest.mock import patch

from . import test_common

class TestMerge(test_common.TestCommon):
    def test_generic_merge(self):
        self._create_rule('x_name', 'exact')

        rec = self._create_record('x_dm_test_model', x_name='toto')
        rec2 = self._create_record('x_dm_test_model', x_name='toto')
        ref = self._create_record('x_dm_test_model_ref', x_name='ref toto', x_test_id=rec2.id)
        self.MyModel.find_duplicates()

        groups = self.env['data_merge.group'].search([('model_id', '=', self.MyModel.id)])
        self.assertEqual(len(groups), 1, 'Should have found 1 group')

        group = groups[0]
        records = group.record_ids
        master_record = records.filtered('is_master')
        other_record = records - master_record

        self.assertEqual(master_record._original_records(), rec, "the 1st record created should be the master")
        self.assertEqual(ref.x_test_id, rec2, "The reference should be to rec2")

        group.merge_records()
        self.assertFalse(other_record.exists(), "record should be unlinked")
        self.assertEqual(ref.x_test_id, rec, "The reference should be to rec")

    def test_generic_insensitive_rule(self):
        self._create_rule('x_name', 'accent')
        for name in ('accentuée', 'accentuee', 'Accentuée', 'Accentué'):
            self._create_record('x_dm_test_model', x_name=name)
        self.MyModel.find_duplicates()

        groups = self.env['data_merge.group'].search([('model_id', '=', self.MyModel.id)])
        self.assertEqual(len(groups), 1, 'Should have found 1 group')
        self.assertEqual(len(groups.record_ids), 3, 'First group must contains three records: ("accentuée", "accentue", "Accentuée")')
        self.assertNotIn('Accentué', groups[0].record_ids.mapped('display_name'), 'Group must not contains "Accentué"')

    def test_mixed_case_fields(self):
        '''
            Tests mixed case fields query on _update_foreign_keys
        '''
        self.DMTestModel3 = self.env['ir.model'].create({
            'name': 'Test Model 3',
            'model': 'x_dm_test_model3',
            'field_id': [
                (0, 0, {'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
                (
                0, 0, {'name': 'x_studio_many2one_field_nKSEu', 'ttype': 'many2one', 'field_description': 'studio test',
                       'relation': 'x_dm_test_model', 'index': True}),
            ]
        })
        self.test_generic_merge()

    def test_cleanup_deleted_records(self):
        self._create_rule('x_name', 'exact')

        self._create_record('x_dm_test_model', x_name='toto')
        rec2 = self._create_record('x_dm_test_model', x_name='toto')
        rec3 = self._create_record('x_dm_test_model', x_name='toto')

        self.MyModel.find_duplicates()

        group = self.env['data_merge.group'].search([('model_id', '=', self.MyModel.id)])

        rec2.unlink()
        self.assertEqual(len(group.record_ids), 3, 'The group must contains 3 records')

        group._cleanup()
        self.assertEqual(len(group.record_ids), 2, 'The group must contains 2 records')

        rec3.unlink()
        group._cleanup()
        self.assertFalse(group.record_ids, 'The group should not contains any records')

    def test_delete_merge_model(self):
        self._create_rule("x_name", "exact")

        self._create_record("x_dm_test_model", x_name="toto")
        self._create_record("x_dm_test_model", x_name="toto")

        # Update the model to notify a user
        user = new_test_user(self.env, login="merge_user", groups="base.group_system")
        self.MyModel.write({
            "merge_mode": "manual",
            "notify_user_ids": [Command.link(user.id)],
        })

        self.MyModel.find_duplicates()
        self.MyModel._notify_new_duplicates()

        group = self.env["data_merge.group"].search(
            [("model_id", "=", self.MyModel.id)]
        )
        messages = self.env["mail.message"].search(
            [("model", "=", "data_merge.model"), ("res_id", "=", self.MyModel.id)]
        )
        self.assertEqual(len(group.record_ids), 2, "The group must contains 2 records")
        self.assertTrue(messages, "Notification messages should have been created")

        self.MyModel.unlink()

        self.assertFalse(group.record_ids, "The group should not contains any records")
        self.assertFalse(messages.exists(), "The messages should have been deleted")

    def test_merge_company_dependent(self):
        company1 = self.env['res.company'].create({'name': "CompanyA"})
        company2 = self.env['res.company'].create({'name': "CompanyB"})

        rec = self._create_record('x_dm_test_model_cd', x_name='toto')
        rec2 = self._create_record('x_dm_test_model_cd', x_name='toto')

        field = self.env['ir.model.fields']._get('x_dm_test_model_cd', 'x_cd')
        fid = field.id
        rec.with_company(company1).write({'x_cd': 'one'})
        rec2.with_company(company1).write({'x_cd': 'twoA'})
        rec2.with_company(company2).write({'x_cd': 'twoB'})
        (rec + rec2).flush_recordset()

        model = self.DMModel.create({
            'name': 'Test Model',
            'res_model_id': self.DMTestModelCompanyDependent.id,
            'merge_mode': 'automatic'
        })

        self.DMRule.create({
            'model_id': model.id,
            'field_id':  self.env['ir.model.fields']._get('x_dm_test_model_cd', 'x_name').id,
            'match_mode': 'exact'
        })

        model.find_duplicates()
        self.assertEqual(rec.with_company(company1).x_cd, 'one', 'The original field value should stay')
        self.assertEqual(rec.with_company(company2).x_cd, 'twoB', 'The new field value should be available on the master record')


@tagged('post_install', '-at_install')
class TestMergeLog(test_common.TestCommon):
    def test_merge_log_note_project_task(self):
        """
        Check that log notes are posted in the chatter of the merged records of a model inheriting from `mail.thread`
        """
        if self.env['ir.module.module']._get('project').state != 'installed':
            self.skipTest("The project module is required to run this test.")

        test_project = self.env['project.project'].create({'name': 'Test project'})
        task_1, task_2, task_3 = self.env['project.task'].create([
            {'name': 'Task 1',  'user_ids': False, 'project_id': test_project.id},
            {'name': 'Task 2',  'user_ids': False, 'project_id': test_project.id},
            {'name': 'Task 3',  'user_ids': False, 'project_id': test_project.id},
        ])

        res_model_id = self.env['ir.model'].search([('model', '=', 'project.task')])
        model_id = self.env['data_merge.model'].create({
            'name': 'project.task',
            'res_model_id': res_model_id.id,
        })
        data_merge_group = self.env['data_merge.group'].create({
            'model_id': model_id.id,
            'res_model_id': res_model_id.id,
            'record_ids': [
                Command.create({'res_id': task_1.id, 'is_master': True}),
                Command.create({'res_id': task_2.id}),
                Command.create({'res_id': task_3.id}),
            ],
        })

        res = data_merge_group.merge_records(data_merge_group.record_ids.ids)

        self.assertEqual(res["records_merged"], 3)
        self.assertIn("merged into this one", task_1.message_ids.sorted(key=lambda m: m.create_date)[0].body)
        self.assertIn("Task merged into", task_2.message_ids.sorted(key=lambda m: m.create_date)[0].body)
        self.assertIn("Task merged into", task_3.message_ids.sorted(key=lambda m: m.create_date)[0].body)
