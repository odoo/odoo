# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged

from .test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install')
class TestProjectMilestone(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.milestone = cls.env['project.milestone'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test Milestone',
            'project_id': cls.project_pigs.id,
        })

    def test_milestones_settings_change(self):
        # To be sure the feature is disabled globally to begin the test.
        self.env['res.config.settings'] \
            .create({'group_project_milestone': False}) \
            .execute()
        self.assertFalse(self.env.user.has_group('project.group_project_milestone'), 'The "Milestones" feature should not be globally enabled by default.')
        self.assertFalse(self.project_pigs.allow_milestones, 'The "Milestones" feature should not be enabled by default.')
        self.env['res.config.settings'] \
            .create({'group_project_milestone': True}) \
            .execute()
        self.assertTrue(self.env.user.has_group('project.group_project_milestone'), 'The "Milestones" feature should globally be enabled.')
        self.assertTrue(self.project_pigs.allow_milestones, 'The "Milestones" feature should be enabled by default on the project when the feature is enabled.')
        project = self.env['project.project'].create({'name': 'Test allow_milestones on New Project'})
        self.assertTrue(project.allow_milestones, 'The "Milestones" feature should be enabled by default when the feature is enabled globally.')

        with Form(self.env['project.project']) as project_form:
            project_form.name = 'My Mouses Project'
            self.assertTrue(project_form.allow_milestones, 'New projects allow_milestones should be True by default.')

    def test_change_project_in_task(self):
        """ Test when a task is linked to a milestone and when we change its project the milestone is removed

            Test Case:
            =========
            1) Set a milestone on the task
            2) Change the project of that task
            3) Check no milestone is linked to the task
        """
        self.task_1.milestone_id = self.milestone
        self.assertEqual(self.task_1.milestone_id, self.milestone)

        self.task_1.project_id = self.project_goats
        self.assertFalse(self.task_1.milestone_id, 'No milestone should be linked to the task since its project has changed')

    def test_duplicate_project_duplicates_milestones_on_tasks(self):
        """
        Test when we duplicate the project with tasks linked to its' milestones,
        that the tasks in the new project are also linked to the duplicated milestones of the new project
        We can't really robustly test that the mapping of task -> milestone is the same in the old and new project,
        the workaround way of testing the mapping is basing ourselves on unique names and check that those are equals in the test.
        """
        # original unique_names, used to map between the original -> copy
        unique_name_1 = "unique_name_1"
        unique_name_2 = "unique_name_2"
        unique_names = [unique_name_1, unique_name_2]
        project = self.env['project.project'].create({'name': 'Test project'})
        milestones = self.env['project.milestone'].create([{
            'name': unique_name_1,
            'project_id': project.id,
        }, {
            'name': unique_name_2,
            'project_id': project.id,
        }])
        tasks = self.env['project.task'].create([{
            'name': unique_name_1,
            'project_id': project.id,
            'milestone_id': milestones[0].id,
        }, {
            'name': unique_name_2,
            'project_id': project.id,
            'milestone_id': milestones[1].id,
        }])
        self.assertEqual(tasks[0].milestone_id, milestones[0])
        self.assertEqual(tasks[1].milestone_id, milestones[1])
        project_copy = project.copy()
        self.assertNotEqual(project_copy.milestone_ids, False)
        self.assertEqual(project.milestone_ids.mapped('name'), project_copy.milestone_ids.mapped('name'))
        self.assertNotEqual(project_copy.task_ids, False)
        for milestone in project_copy.task_ids.milestone_id:
            self.assertTrue(milestone in project_copy.milestone_ids)
        for unique_name in unique_names:
            orig_task = project.task_ids.filtered(lambda t: t.name == unique_name)
            copied_task = project_copy.task_ids.filtered(lambda t: t.name == unique_name)
            self.assertEqual(orig_task.name, copied_task.name, "The copied_task should be a copy of the original task")
            self.assertNotEqual(copied_task.milestone_id, False,
                                "We should copy the milestone and it shouldn't be reset to false from _compute_milestone_id")
            self.assertEqual(orig_task.milestone_id.name, copied_task.milestone_id.name,
                             "the copied milestone should be a copy if the original ")
