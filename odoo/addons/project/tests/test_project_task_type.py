# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestProjectTaskType(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super(TestProjectTaskType, cls).setUpClass()

        cls.stage_created = cls.env['project.task.type'].create({
            'name': 'Stage Already Created',
            'project_ids': cls.project_goats.ids,
        })

    def test_create_stage(self):
        '''
        Verify that 'user_id' is removed when a stage is created with `project_ids` set or set by default to the curent user if not
        '''
        self.assertFalse(self.env['project.task.type'].create({
                'name': 'New Stage',
                'user_id': self.uid,
                'project_ids': [self.project_goats.id],
            }).user_id,
            "user_id should be reset if a project is set on the current stage",
        )
        self.assertEqual(self.env['project.task.type'].create({
                'name': 'Other new Stage',
            }).user_id.id,
            self.env.uid,
            "user_id should be set to the current user if no project is set at stage creation",
        )

    def test_modify_existing_stage(self):
        '''
        - case 1: [`user_id`: not set, `project_ids`: set]  | Remove `project_ids` => user_id should not be set (no transformation of project stage to personal stage)
        - case 2: [`user_id`: not set, `project_ids`: not set] | Add `user_id` and `project_ids` => user_id reset
        - case 3: [`user_id`: not set, `project_ids`: set] | Add `user_id` => UserError
        - case 4: [`user_id`: set, `project_ids`: not set]  | Add `project_ids` => user_id reset
        '''
        # case 1
        self.assertTrue(not self.stage_created.user_id and self.stage_created.project_ids)
        self.stage_created.write({'project_ids': False})
        self.assertFalse(
            self.stage_created.user_id,
            "When project_ids is reset, user_id should not be set (no transformation of project related stage to personal stage)",
        )

        # case 2
        self.assertTrue(not self.stage_created.user_id and not self.stage_created.project_ids)
        self.stage_created.write({
            'user_id': self.uid,
            'project_ids': [self.project_goats.id],
        })
        self.assertFalse(
            self.stage_created.user_id,
            "user_id should be reset if a project is set on the current stage",
        )

        # case 3
        with self.assertRaises(UserError):
            self.stage_created.write({
                'user_id': self.uid,
            })

        # case 4
        self.stage_created.write({
            'user_id': self.env.uid,
            'project_ids': False,
        })
        self.assertTrue(self.stage_created.user_id)
        self.stage_created.write({
            'project_ids': [self.project_goats.id],
        })
        self.assertFalse(
            self.stage_created.user_id,
            "user_id should be reset if a project is set on the current stage",
        )
