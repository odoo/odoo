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
