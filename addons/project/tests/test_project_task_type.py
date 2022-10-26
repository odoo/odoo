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
        })

    def test_create_stage(self):
        '''
        Verify that it is not possible to add to a newly created stage a `user_id` and a `project_ids`
        '''
        with self.assertRaises(UserError):
            self.env['project.task.type'].create({
                'name': 'New Stage',
                'user_id': self.uid,
                'project_ids': [self.project_goats.id],
            })

    def test_modify_existing_stage(self):
        '''
        - case 1: [`user_id`: not set, `project_ids`: not set] | Add `user_id` and `project_ids` => UserError
        - case 2: [`user_id`: set, `project_ids`: not set]  | Add `project_ids` => UserError
        - case 3: [`user_id`: not set, `project_ids`: set] | Add `user_id` => UserError
        '''
        # case 1
        with self.assertRaises(UserError):
            self.stage_created.write({
                'user_id': self.uid,
                'project_ids': [self.project_goats.id],
            })

        # case 2
        self.stage_created.write({
            'user_id': self.uid,
        })
        with self.assertRaises(UserError):
            self.stage_created.write({
                'project_ids': [self.project_goats.id],
            })

        # case 3
        self.stage_created.write({
            'user_id': False,
            'project_ids': [self.project_goats.id],
        })
        with self.assertRaises(UserError):
            self.stage_created.write({
                'user_id': self.uid,
            })
