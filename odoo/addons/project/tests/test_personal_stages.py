# -*- coding: utf-8 -*-

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from .test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install', 'personal_stages')
class TestPersonalStages(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_stages = cls.env['project.task.type'].search([('user_id', '=', cls.user_projectuser.id)])
        cls.manager_stages = cls.env['project.task.type'].search([('user_id', '=', cls.user_projectmanager.id)])

    def test_personal_stage_base(self):
        # Project User is assigned to task_1 he should be able to see a personal stage
        self.task_1.with_user(self.user_projectuser)._compute_personal_stage_id()
        self.assertTrue(self.task_1.with_user(self.user_projectuser).personal_stage_type_id,
            'Project User is assigned to task 1, he should have a personal stage assigned.')

        self.task_1.with_user(self.user_projectmanager)._compute_personal_stage_id()
        self.assertFalse(self.env['project.task'].browse(self.task_1.id).with_user(self.user_projectmanager).personal_stage_type_id,
            'Project Manager is not assigned to task 1, he should not have a personal stage assigned.')

        # Now assign a second user to our task_1
        self.task_1.user_ids += self.user_projectmanager
        self.assertTrue(self.task_1.with_user(self.user_projectmanager).personal_stage_type_id,
            'Project Manager has now been assigned to task 1 and should have a personal stage assigned.')

        self.task_1.with_user(self.user_projectmanager)._compute_personal_stage_id()
        task_1_manager_stage = self.task_1.with_user(self.user_projectmanager).personal_stage_type_id

        self.task_1.with_user(self.user_projectuser)._compute_personal_stage_id()
        self.task_1.with_user(self.user_projectuser).personal_stage_type_id = self.user_stages[1]
        self.assertEqual(self.task_1.with_user(self.user_projectuser).personal_stage_type_id, self.user_stages[1],
            'Assigning another personal stage to the task should have changed it for user 1.')

        self.task_1.with_user(self.user_projectmanager)._compute_personal_stage_id()
        self.assertEqual(self.task_1.with_user(self.user_projectmanager).personal_stage_type_id, task_1_manager_stage,
            'Modifying the personal stage of Project User should not have affected the personal stage of Project Manager.')

        self.task_2.with_user(self.user_projectmanager).personal_stage_type_id = self.manager_stages[1]
        self.assertEqual(self.task_1.with_user(self.user_projectmanager).personal_stage_type_id, task_1_manager_stage,
            'Modifying the personal stage on task 2 for Project Manager should not have affected the stage on task 1.')

    def test_personal_stage_search(self):
        self.task_2.user_ids += self.user_projectuser
        # Make sure both personal stages are different
        self.task_1.with_user(self.user_projectuser).personal_stage_type_id = self.user_stages[0]
        self.task_2.with_user(self.user_projectuser).personal_stage_type_id = self.user_stages[1]
        tasks = self.env['project.task'].with_user(self.user_projectuser).search([('personal_stage_type_id', '=', self.user_stages[0].id)])
        self.assertTrue(tasks, 'The search result should not be empty.')
        for task in tasks:
            self.assertEqual(task.personal_stage_type_id, self.user_stages[0],
                'The search should only have returned task that are in the inbox personal stage.')

    def test_personal_stage_read_group(self):
        self.task_1.user_ids += self.user_projectmanager
        self.task_1.with_user(self.user_projectmanager).personal_stage_type_id = self.manager_stages[1]
        #Makes sure the personal stage for project manager is saved in the database
        self.env.flush_all()
        read_group_user = self.env['project.task'].with_user(self.user_projectuser).read_group(
            [('user_ids', '=', self.user_projectuser.id)], fields=['sequence:avg'], groupby=['personal_stage_type_ids'])
        # Check that the result is at least a bit coherent
        self.assertEqual(len(self.user_stages), len(read_group_user),
            'read_group should return %d groups' % len(self.user_stages))
        # User has only one task assigned the sum of all counts should be 1
        total = 0
        for group in read_group_user:
            total += group['personal_stage_type_ids_count']
        self.assertEqual(1, total,
            'read_group should not have returned more tasks than the user is assigned to.')
        read_group_manager = self.env['project.task'].with_user(self.user_projectmanager).read_group(
            [('user_ids', '=', self.user_projectmanager.id)], fields=['sequence:avg'], groupby=['personal_stage_type_ids'])
        self.assertEqual(len(self.manager_stages), len(read_group_manager),
            'read_group should return %d groups' % len(self.user_stages))
        total = 0
        total_stage_0 = 0
        total_stage_1 = 0
        for group in read_group_manager:
            total += group['personal_stage_type_ids_count']
            # Check that we have a task in both stages
            if group['personal_stage_type_ids'][0] == self.manager_stages[0].id:
                total_stage_0 += 1
            elif group['personal_stage_type_ids'][0] == self.manager_stages[1].id:
                total_stage_1 += 1
        self.assertEqual(2, total,
            'read_group should not have returned more tasks than the user is assigned to.')
        self.assertEqual(1, total_stage_0)
        self.assertEqual(1, total_stage_1)

    def test_default_personal_stage(self):
        user_without_stage, user_with_stages = self.env['res.users'].create([{
            'login': 'test_no_stage',
            'name': "Test User without stage",
        }, {
            'login': 'test_stages',
            'name': "Test User with stages",
        }])
        personal_stage = self.env['project.task.type'].create({
            'name': 'personal stage',
            'user_id': user_with_stages.id,
        })
        ProjectTaskTypeSudo = self.env['project.task.type'].sudo()
        # ensure that a user without personal stage is getting the default stages
        self.task_1.with_user(user_without_stage)._ensure_personal_stages()
        stages = ProjectTaskTypeSudo.search([('user_id', '=', user_without_stage.id)])
        self.assertEqual(len(stages), 7, "As this user had no personal stage, the default ones should have been created for him")
        # ensure that the user's personal stages are not changing if the user already had some
        self.task_1.with_user(user_with_stages)._ensure_personal_stages()
        stages = ProjectTaskTypeSudo.search([('user_id', '=', user_with_stages.id)])
        self.assertEqual(stages, personal_stage, "As this user already had a personal stage, none should be added")

    def test_delete_personal_stage(self):
        """
        When deleting personal stages, the task of this stage are transfered to the one following it sequence-wise.
        The deletion of stages can be done in batch.
        """
        user_1, user_2, user_3 = self.env['res.users'].create([{
            'login': 'user_1_stages',
            'name': 'User 1 with personal stages',
        }, {
            'login': 'user_2_stages',
            'name': 'User 2 with personal stages',
        }, {
            'login': 'user_3_stages',
            'name': 'User 3 with personal stages',
        }])

        # Users should have no personal stage and no tasks as one has not access My Tasks or To-do views
        self.assertEqual(self.env['project.task.type'].search_count([('user_id', '=', user_1.id)]), 0)
        self.assertEqual(self.env['project.task.type'].search_count([('user_id', '=', user_2.id)]), 0)
        self.assertEqual(self.env['project.task'].search_count([('user_ids', 'in', user_1.ids)]), 0)
        self.assertEqual(self.env['project.task'].search_count([('user_ids', 'in', user_2.ids)]), 0)

        # Create 5 personal stages for user 1
        user_1_stages = self.env['project.task.type'].create([{
            'user_id': user_1.id,
            'name': f'User 1 - Stage {i}',
            'sequence': 10 * i,
        } for i in range(1, 6)])
        # Create 3 personal stages for user 2
        user_2_stages = self.env['project.task.type'].create([{
            'user_id': user_2.id,
            'name': f'User 2 - Stage {i}',
            'sequence': 10 * i,
        } for i in range(1, 4)])

        # Create private tasks for user 1 and 2
        private_tasks = self.env['project.task'].create([{
            'user_ids': [Command.link(user_1.id), Command.link(user_2.id)],
            'name': 'Task 1',
            'project_id': False,
        }, {
            'user_ids': [Command.link(user_1.id), Command.link(user_2.id)],
            'name': 'Task 2',
            'project_id': False,
        }, {
            'user_ids': [Command.link(user_1.id)],
            'name': 'Task 3',
            'project_id': False,
        }, {
            'user_ids': [Command.link(user_1.id)],
            'name': 'Task 4',
            'project_id': False,
        }])

        # Put private tasks in personal stages for user 1
        private_tasks[0].with_user(user_1.id).personal_stage_type_id = user_1_stages[2].id
        private_tasks[1].with_user(user_1.id).personal_stage_type_id = user_1_stages[3].id
        private_tasks[2].with_user(user_1.id).personal_stage_type_id = user_1_stages[4].id
        private_tasks[3].with_user(user_1.id).personal_stage_type_id = user_1_stages[4].id

        # Put private tasks in personal stages for user 2
        private_tasks[0].with_user(user_2.id).personal_stage_type_id = user_2_stages[0].id
        private_tasks[1].with_user(user_2.id).personal_stage_type_id = user_2_stages[1].id

        # ------------------------------------
        # ------- A. Initial situation  ------
        # ------------------------------------
        #
        # For user 1:
        #
        #  +---------+---------+---------+---------+---------+
        #  | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Stage 5 |
        #  +---------+---------+---------+---------+---------+
        #  |         |         | Task 1  | Task 2  | Task 3  |
        #  |         |         |         |         | Task 4  |
        #  +---------+---------+---------+---------+---------+
        #
        # For user 2:
        #
        #  +---------+---------+---------+
        #  | Stage 1 | Stage 2 | Stage 3 |
        #  +---------+---------+---------+
        #  | Task 1  | Task 2  |         |
        #  +---------+---------+---------+

        self.assertEqual(self.env['project.task.type'].with_user(user_1.id).search_count([('project_ids', '=', False), ('user_id', '=', user_1.id)]), 5)
        self.assertEqual(self.env['project.task'].with_user(user_1.id).search_count([('user_ids', 'in', user_1.ids)]), 4)
        private_tasks.invalidate_recordset(['personal_stage_type_id'])
        self.assertEqual(private_tasks[0].with_user(user_1.id).personal_stage_type_id.id, user_1_stages[2].id)
        self.assertEqual(private_tasks[1].with_user(user_1.id).personal_stage_type_id.id, user_1_stages[3].id)
        self.assertEqual(private_tasks[2].with_user(user_1.id).personal_stage_type_id.id, user_1_stages[4].id)
        self.assertEqual(private_tasks[3].with_user(user_1.id).personal_stage_type_id.id, user_1_stages[4].id)
        self.assertEqual(self.env['project.task.type'].with_user(user_2.id).search_count([('project_ids', '=', False), ('user_id', '=', user_2.id)]), 3)
        self.assertEqual(self.env['project.task'].with_user(user_2.id).search_count([('user_ids', 'in', user_2.ids)]), 2)
        private_tasks.invalidate_recordset(['personal_stage_type_id'])
        self.assertEqual(private_tasks[0].with_user(user_2.id).personal_stage_type_id.id, user_2_stages[0].id)
        self.assertEqual(private_tasks[1].with_user(user_2.id).personal_stage_type_id.id, user_2_stages[1].id)

        # --------------------------------------------
        # ---- B. Deleting an empty (own) stage  -----
        # --------------------------------------------
        #
        # Deleting stage 3 for user 2
        # Expected result for user 2:
        #
        #  +---------+---------+
        #  | Stage 1 | Stage 2 |
        #  +---------+---------+
        #  | Task 1  | Task 2  |
        #  +---------+---------+

        user_2_stages[2].with_user(user_2.id).unlink()
        self.assertEqual(self.env['project.task.type'].with_user(user_2.id).search_count([('project_ids', '=', False), ('user_id', '=', user_2.id)]), 2,
                         "A user should be able to unlink its own (empty) personal stage.")

        # --------------------------------------------
        # ---- C. Deleting a single (own) stage  -----
        # --------------------------------------------
        #
        # Deleting stage 3 for user 1, the task in this stage should move to stage 2
        # Expected result for user 1:
        #
        #  +---------+---------+---------+---------+
        #  | Stage 1 | Stage 2 | Stage 4 | Stage 5 |
        #  +---------+---------+---------+---------+
        #  |         | Task 1  | Task 2  | Task 3  |
        #  |         |         |         | Task 4  |
        #  +---------+---------+---------+---------+

        private_tasks.invalidate_recordset(['personal_stage_type_id'])
        user_1_stages[2].with_user(user_1.id).unlink()
        self.assertEqual(self.env['project.task.type'].with_user(user_1.id).search_count([('project_ids', '=', False), ('user_id', '=', user_1.id)]), 4,
                         "A user should be able to unlink its own personal stage.")
        self.assertEqual(self.env['project.task'].with_user(user_1.id).search_count([('user_ids', 'in', user_1.ids)]), 4,
                         "Tasks in a removed personal stage should not be unlinked.")
        self.assertEqual(private_tasks[0].with_user(user_1.id).personal_stage_type_id.id, user_1_stages[1].id,
                         "Tasks in a removed personal stage should be moved to the stage following it sequence-wise")

        # --------------------------------------------
        # ---- D. Deleting (own) stage in batch ------
        # --------------------------------------------
        #
        # Deleting stages 2 & 4 for user 1, the task in those stages should move to stage 1
        # Expected result for user 1:
        #
        #  +---------+---------+
        #  | Stage 1 | Stage 5 |
        #  +---------+---------+
        #  | Task 1  | Task 3  |
        #  | Task 2  | Task 4  |
        #  +---------+---------+

        user_1_stages.filtered(lambda s: s.id in [user_1_stages[1].id, user_1_stages[3].id]).with_user(user_1.id).unlink()
        self.assertEqual(self.env['project.task.type'].with_user(user_1.id).search_count([('project_ids', '=', False), ('user_id', '=', user_1.id)]), 2,
                         "A user should be able to unlink its own personal stage in batch.")
        self.assertEqual(self.env['project.task'].with_user(user_1.id).search_count([('user_ids', 'in', user_1.ids)]), 4,
                         "Tasks in personal stages removed in batch should not be unlinked.")
        for i in range(2):
            self.assertEqual(private_tasks[i].with_user(user_1.id).personal_stage_type_id.id, user_1_stages[0].id,
                             "Tasks in a personal stage removed in batch should be moved to the stage following it sequence-wise")

        # ------------------------------------------------------
        # -- E. Deleting multi-user stages in batch (as sudo) --
        # ------------------------------------------------------
        #
        # Deleting stages 1 user 1 and stage 2 for user 2
        # Expected result for user 1:
        #
        #  +---------+
        #  | Stage 5 |
        #  +---------+
        #  | Task 1  |
        #  | Task 2  |
        #  | Task 3  |
        #  | Task 4  |
        #  +---------+
        #
        # Expected result for user 2:
        #
        #  +---------+
        #  | Stage 1 |
        #  +---------+
        #  | Task 1  |
        #  | Task 2  |
        #  +---------+
        #

        (user_1_stages[0] | user_2_stages[1]).sudo().unlink()
        self.assertEqual(self.env['project.task.type'].with_user(user_1.id).search_count([('project_ids', '=', False), ('user_id', '=', user_1.id)]), 1,
                         "Superuser should be able to delete personal stages in batch.")
        self.assertEqual(self.env['project.task.type'].with_user(user_2.id).search_count([('project_ids', '=', False), ('user_id', '=', user_2.id)]), 1,
                         "Superuser should be able to delete personal stages in batch.")
        self.assertEqual(self.env['project.task'].with_user(user_1.id).search_count([('user_ids', 'in', user_1.ids)]), 4,
                         "Tasks in personal stages removed in batch by superuser should not be unlinked.")
        for private_task in private_tasks:
            self.assertEqual(private_task.with_user(user_1.id).personal_stage_type_id.id, user_1_stages[4].id,
                             "Tasks in a personal stage removed in batch should be moved to a stage with a higher sequence if no stage with lower sequence have been found")
        private_tasks.invalidate_recordset(['personal_stage_type_id'])
        self.assertEqual(private_tasks[0].with_user(user_2.id).personal_stage_type_id.id, user_2_stages[0].id,
                         "Tasks in a personal stage removed in batch by superuser should be moved to the stage following it sequence-wise")
        self.assertEqual(private_tasks[1].with_user(user_2.id).personal_stage_type_id.id, user_2_stages[0].id,
                         "Tasks in a personal stage removed in batch by superuser should be moved to the stage following it sequence-wise")

        # ------------------------------------------------------
        # -- F. Deleting the last personal stage not allowed  --
        # ------------------------------------------------------
        #
        # Deleting stage 1 for user 2 should raise an error
        # Expected result for user 2:
        #
        #  +---------+
        #  | Stage 1 |
        #  +---------+
        #  | Task 1  |
        #  | Task 2  |
        #  +---------+
        #

        with self.assertRaises(UserError, msg="Deleting the last personal stage of a user should raise an error"):
            user_2_stages[0].with_user(user_2.id).unlink()
        self.assertEqual(self.env['project.task.type'].with_user(user_2.id).search_count([('project_ids', '=', False), ('user_id', '=', user_2.id)]), 1,
                         "Last personal stage of a user should not be deleted by unlink method")
        private_tasks.invalidate_recordset(['personal_stage_type_id'])
        self.assertEqual(private_tasks[0].with_user(user_2.id).personal_stage_type_id.id, user_2_stages[0].id,
                         "Last personal stage of a user should not be deleted by unlink method")
        self.assertEqual(private_tasks[1].with_user(user_2.id).personal_stage_type_id.id, user_2_stages[0].id,
                         "Last personal stage of a user should not be deleted by unlink method")

        # -------------------------------------------------------------------
        # - G. Deleting the last personal stage not allowed (even if empty) -
        # -------------------------------------------------------------------

        empty_stage_user_3 = self.env['project.task.type'].create({
            'user_id': user_3.id,
            'name': 'User 3 - Empty stage',
            'sequence': 10,
        })

        with self.assertRaises(UserError, msg="Deleting the last personal stage of a user should raise an error, even if the stage is empty"):
            empty_stage_user_3.with_user(user_3.id).unlink()

        # ---------------------------------------------------------
        # - H. Mixed scenario: 1 normal stage and 2 personal ones -
        # ---------------------------------------------------------

        # Create one normal project stage with no task in it two other personal stages for both users that could be deleted
        empty_stages = self.env['project.task.type'].create([{
            'user_id': user_1.id,
            'name': 'User 1 - Empty stage',
            'sequence': 10,
        }, {
            'user_id': user_2.id,
            'name': 'User 2 - Empty stage',
            'sequence': 10,
        }, {
            'project_ids': self.project_pigs,
            'name': 'Empty stage in project Pigs',
            'sequence': 10,
        }])
        empty_stages.sudo().unlink()
        self.assertFalse(self.env['project.task.type'].search_count([('id', 'in', empty_stages.ids)]),
                         "All stages, wether they are personal or not, should be able to be deleted in batch")

@tagged('-at_install', 'post_install')
class TestPersonalStageTour(HttpCase, TestProjectCommon):

    def test_personal_stage_tour(self):
        # Test customizing personal stages as a project user
        self.start_tour('/web', 'personal_stage_tour', login="armandel")
