# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests.common import Form


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

    def test_task_in_folded_stage_must_be_closed(self):
        unfolded_stage = self.env['project.task.type'].create({'name': 'Progress', 'sequence': 1, 'fold': False})
        folded_stage = self.env['project.task.type'].create({'name': 'Won', 'sequence': 2, 'fold': True})

        project = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'rev',
            'privacy_visibility': 'employees',
            'alias_name': 'rev',
            'partner_id': self.partner_1.id,
            'type_ids': [unfolded_stage.id, folded_stage.id],
        })

        task = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs UserTask',
            'user_ids': self.user_projectuser,
            'project_id': project.id,
            'stage_id': unfolded_stage.id})

        self.assertFalse(task.is_closed)

        with Form(task.with_context({'mail_create_nolog': True})) as task_form:
            task_form.stage_id = folded_stage

        self.assertTrue(task.is_closed, "task in folded stage should be closed")
