# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
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

    def test_group_by_personal_stage(self):
        """
        Check the consistence of search_read and read_group when one groups project.tasks by personal stages.

        Supose we have a user and his manager. Group all tasks by personal stage in the "list view".
        A `web_read_group` is performed to classify the tasks and a `web_search_read` is performed to display the lines.
        We check the consitency of both operations for tasks that are not linked to a personal stage of the current user.
        """

        if 'hr.employee' not in self.env:
            self.skipTest("This test requires to set a manager")
        project = self.project_goats
        user = self.user_projectmanager
        manager_user = self.env['res.users'].create({
            'name': 'Roger Employee',
            'login': 'Roger',
            'email': 'rog.projectmanager@example.com',
            'groups_id': [Command.set([self.ref('base.group_user'), self.ref('project.group_project_manager')])],
        })
        manager = self.env['hr.employee'].create({
            'user_id': manager_user.id,
            'image_1920': False,
        })
        (user | manager_user).employee_id.write({'parent_id': manager.id})
        user_personal_stages = self.env['project.task.type'].search([('user_id', '=', user.id)])
        # we create tasks for the user with different types of assignement
        self.env['project.task'].with_user(user).create([
            {
                'name': f"Task: {stage.id}",
                'project_id': project.id,
                'personal_stage_type_id': stage.id,
                'user_ids': [Command.link(user.id)],
            }
            for stage in user_personal_stages],
        )
        self.env['project.task'].with_user(user).create([
            {
                'name': f"Task: {stage.id}",
                'project_id': project.id,
                'personal_stage_type_id': stage.id,
                'user_ids': [Command.link(user.id), Command.link(manager_user.id)],
            }
            for stage in user_personal_stages],
        )
        # this task is created to create the default personal stages of manager user
        self.env['project.task'].with_user(manager_user).create({
            'name': "Manager's task",
            'project_id': project.id,
            'user_ids': [Command.link(manager_user.id)],
        })
        manager_user_personal_stages = self.env['project.task.type'].search([('user_id', '=', manager_user.id)])
        self.env['project.task'].with_user(manager_user).create([
            {
                'name': f"Task : {stage.id}",
                'project_id': project.id,
                'stage_id': stage.id,
                'user_ids': [Command.link(manager_user.id)],
            }
            for stage in manager_user_personal_stages],
        )

        self.env.uid = user.id
        base_domain = [("user_ids.employee_parent_id.user_id", "=", manager_user.id)]
        tasks = self.env['project.task'].with_user(user.id).search(base_domain)
        tasks_with_personal_stage = tasks.filtered(lambda t: user in t.personal_stage_type_id.user_id)
        tasks_without_personal_stage = tasks - tasks_with_personal_stage
        fields = [
            "id",
            "name",
            "project_id",
            "milestone_id",
            "partner_id",
            "user_ids",
            "activity_ids",
            "stage_id",
            "personal_stage_type_ids",
            "tag_ids",
            "priority",
            "company_id",
        ]
        groupby = ["personal_stage_type_ids"]
        user_read_group = self.env['project.task'].with_user(user).read_group(domain=base_domain, fields=fields, groupby=groupby)
        number_of_tasks_in_groups = sum(gr['personal_stage_type_ids_count'] if gr['personal_stage_type_ids'] and gr['personal_stage_type_ids'][0] in user_personal_stages.ids else 0 for gr in user_read_group)
        self.assertEqual(len(tasks_with_personal_stage), number_of_tasks_in_groups)
        tasks_found_for_user = [task['id'] for task in self.env['project.task'].with_user(user.id).search_read(domain=base_domain, fields=fields)]
        self.assertEqual(tasks.ids, tasks_found_for_user)
        domain = ["&", ("personal_stage_type_ids", "=", False), ("user_ids.employee_parent_id.user_id", "=", manager_user.id)]
        tasks_diplayed_without_personal_stage = [task['id'] for task in self.env['project.task'].with_user(user.id).search_read(domain=domain, fields=fields)]
        self.assertEqual(tasks_without_personal_stage.ids, tasks_diplayed_without_personal_stage)
