# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import Form, tagged
from dateutil.relativedelta import relativedelta

from .test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install')
class TestProjectMilestone(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('project.group_project_milestone')
        cls.milestone_pigs, cls.milestone_goats = cls.env['project.milestone'].with_context({'mail_create_nolog': True}).create([{
            'name': 'Milestone Pigs',
            'project_id': cls.project_pigs.id,
        }, {
            'name': 'Milestone Goats',
            'project_id': cls.project_goats.id,
        }])

    def test_milestones_settings_change(self):
        # To be sure the feature is disabled globally to begin the test.
        self.env.user.group_ids -= self.env.ref('project.group_project_milestone')
        project1 = self.env['project.project'].create({'name': 'Test allow_milestones on New Project'})
        self.assertFalse(project1.allow_milestones, 'The "Milestones" feature should be disabled by default when the feature is disabled globally.')
        with Form(self.env['project.project']) as project_form:
            project_form.name = 'My Mouses Project'
            self.assertFalse(project_form.allow_milestones, 'New projects allow_milestones should be False by default.')

        # Now, enable the feature
        self.env.user.group_ids |= self.env.ref('project.group_project_milestone')
        project2 = self.env['project.project'].create({'name': 'Test allow_milestones on New Project'})
        self.assertFalse(project2.allow_milestones, 'The "Milestones" feature should still be disabled by default when the feature is enabled globally.')
        with Form(self.env['project.project']) as project_form:
            project_form.name = 'My Mouses Project'
            self.assertFalse(project_form.allow_milestones, 'New projects allow_milestones should be False by default.')

    def test_change_project_in_task(self):
        """ Test when a task is linked to a milestone and when we change its project the milestone is removed (and
            we fallback on the parent milestone if it belongs to the same project)

            Test Case:
            =========
            1) Set a milestone on the task
            2) Change the project of that task
            3) Check no milestone is linked to the task (or the one of its parent is used if relevant)
        """
        # A. No parent task
        self.task_1.milestone_id = self.milestone_pigs
        self.assertEqual(self.task_1.milestone_id, self.milestone_pigs)


        self.task_1.project_id = self.project_goats
        self.assertFalse(self.task_1.milestone_id, 'No milestone should be linked to the task since its project has changed')

        # B. Parent task with no milestone set
        task_2 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Child MilestoneTask',
            'user_ids': self.user_projectmanager,
            'project_id': self.project_pigs.id,
            'parent_id': self.task_1.id,
            'milestone_id': self.milestone_pigs.id,
        })
        self.assertEqual(task_2.milestone_id, self.milestone_pigs)

        task_2.project_id = self.project_goats
        self.assertFalse(task_2.milestone_id, 'No milestone should be linked to the task since its project has changed and its parent task has no milestone')

        # C. Parent task with a milestone set but on a different project
        self.task_1.project_id = self.project_pigs
        self.task_1.milestone_id = self.milestone_pigs
        task_2.project_id = self.project_pigs
        task_2.milestone_id = self.milestone_pigs
        self.assertEqual(task_2.milestone_id, self.milestone_pigs)

        task_2.project_id = self.project_goats
        self.assertFalse(task_2.milestone_id, 'No milestone should be linked to the task since its project has changed and its parent task belongs to another project')

        # D. Parent task with a milestone set on the same project
        self.task_1.project_id = self.project_goats
        self.task_1.milestone_id = self.milestone_goats
        task_2.project_id = self.project_pigs
        task_2.milestone_id = self.milestone_pigs
        self.assertEqual(task_2.milestone_id, self.milestone_pigs)
        task_2.project_id = self.project_goats
        self.assertEqual(task_2.milestone_id, self.milestone_goats,
                         'The milestone of the task should be replaced by the one of its parent task as they now belong to the same project')

        # E. No milestone for private task
        task_2.parent_id = False
        self.assertEqual(task_2.milestone_id, self.milestone_goats)
        task_2.project_id = False
        self.assertFalse(task_2.milestone_id, 'No milestone should be linked to a private task')

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
        project = self.env['project.project'].create({
            'name': 'Test project',
            'allow_milestones': True,
        })
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
                             "the copied milestone should be a copy of the original ")

    def test_duplicate_project_with_milestones_disabled(self):
        """ This test ensures that when a project that has some milestones linked to it but with the milesones feature disabled is copied,
            the copy does not have the feature enabled, and none of the milestones have been copied."""
        extra_milestone_pigs = self.env['project.milestone'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test Extra Milestone',
            'project_id': self.project_pigs.id,
        })

        self.task_1.milestone_id = self.milestone_pigs
        self.task_2.milestone_id = extra_milestone_pigs
        self.project_pigs.allow_milestones = False
        project_copied = self.project_pigs.copy()
        project_copied.task_ids._compute_milestone_id()
        self.assertFalse(project_copied.allow_milestones, "The project copied should have the milestone feature disabled")
        self.assertFalse(project_copied.milestone_ids, "The project copied should not have any milestone")
        self.assertFalse(project_copied.task_ids.milestone_id, "None of the project's task should have a milestone")

    def test_basic_milestone_write(self):
        """ Testing basic milestone/project write operation on task, i.e:
                1. Set/change the milestone of a task
                2. Change the milestone/project of a task simultaneously
                3. Set/change to an invalid milestone
        """
        extra_milestone_pigs = self.env['project.milestone'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test Extra Milestone',
            'project_id': self.project_pigs.id,
        })

        # 1. Set/change the milestone of a task
        self.task_1.project_id = self.project_pigs
        self.assertEqual(self.task_1.project_id, self.project_pigs)
        self.assertFalse(self.task_1.milestone_id)

        self.task_1.milestone_id = self.milestone_pigs
        self.assertEqual(self.task_1.milestone_id, self.milestone_pigs,
                         "Assignation of a valid milestone to a task with no milestone is not working properly.")
        self.task_1.milestone_id = extra_milestone_pigs
        self.assertEqual(self.task_1.milestone_id, extra_milestone_pigs,
                         "Change of the milestone of a task to a milestone from the same project is not working properly.")

        # 2. Change the milestone/project of a task simultaneously
        self.assertEqual(self.task_1.project_id, self.project_pigs)
        self.assertEqual(self.task_1.milestone_id, extra_milestone_pigs)

        self.task_1.write({
            'milestone_id': self.milestone_goats.id,
            'project_id': self.project_goats.id,
        })
        self.assertEqual(self.task_1.milestone_id, self.milestone_goats,
                         "Changing the project of a task and its milestone simultaneously is not working properly.")
        self.assertEqual(self.task_1.project_id, self.project_goats,
                         "Changing the project of a task and its milestone simultaneously is not working properly.")

        # 3. Set/change to an invalid milestone
        self.assertEqual(self.task_1.project_id, self.project_goats)
        self.assertEqual(self.task_1.milestone_id, self.milestone_goats)

        self.task_1.milestone_id = self.milestone_pigs
        self.assertFalse(self.task_1.milestone_id,
                         "Setting the milestone of a task to an invalid value should reset the value of milestone_id.")


    def test_set_milestone_parent_task(self):
        """ When a milestone is set on a parent task, it is set as well on its child tasks if they have no milestone set yet and
            if they belong to the same project (or they have no project set).

            Test Case:
            =========
            1) Set a milestone on the task (or not)
            2) Change the milestone of its parent
            3) Check the result
        """
        # A. Child task with no milestone set and belonging to the same project
        task_2, task_3 = self.env['project.task'].with_context({'mail_create_nolog': True}).create([{
            'name': 'Child MilestoneTask',
            'user_ids': self.user_projectmanager,
            'project_id': self.project_pigs.id,
            'parent_id': self.task_1.id,
        }, {
            'name': 'Grand-child MilestoneTask',
            'user_ids': self.user_projectmanager,
            'project_id': self.project_pigs.id,
        }])
        self.assertFalse(self.task_1.milestone_id)
        self.assertFalse(task_2.milestone_id)

        self.task_1.milestone_id = self.milestone_pigs
        self.assertEqual(task_2.milestone_id, self.milestone_pigs,
                         "The milestone of the parent task should be set to its subtasks if they belong to the same project (or the subtask has not project set) and the subtask has no milestone already set.")

        # B. Child task with a milestone already set
        extra_milestone_pigs = self.env['project.milestone'].with_context({'mail_create_nolog': True}).create({
            'name': 'Extra Milestone Pigs',
            'project_id': self.project_pigs.id,
        })
        self.task_1.milestone_id = False
        task_2.milestone_id = extra_milestone_pigs
        self.assertFalse(self.task_1.milestone_id)
        self.assertEqual(task_2.milestone_id, extra_milestone_pigs)

        self.task_1.milestone_id = self.milestone_pigs
        self.assertEqual(task_2.milestone_id, extra_milestone_pigs, "The milestone of the child task should not be modified has it has already one set.")

        # C. Child task with no milestone set but belonging to another project
        task_2.project_id = self.project_goats
        self.assertFalse(task_2.milestone_id)
        self.task_1.milestone_id = extra_milestone_pigs
        self.assertFalse(task_2.milestone_id, "The milestone of the parent task should not be set to its child task as they belong to different projects.")

        # D. Recursion test (grand-parent task's milestone set to grand-child task)
        task_3.parent_id = task_2
        self.task_1.project_id = task_2.project_id = task_3.project_id = self.project_pigs
        self.task_1.milestone_id = task_2.milestone_id = task_3.milestone_id = False
        self.assertFalse(task_2.milestone_id)
        self.assertFalse(task_3.milestone_id)

        self.task_1.milestone_id = self.milestone_pigs
        self.assertEqual(task_3.milestone_id, self.milestone_pigs, "The milestone of the parent task should be set to its (grand)child tasks recursively.")

        # E. Recursion test 2 (grand-child task has no milestone but first level child does)
        self.task_1.milestone_id = False
        task_2.milestone_id = self.milestone_pigs
        task_3.milestone_id = False
        self.assertFalse(self.task_1.milestone_id)
        self.assertFalse(task_3.milestone_id)
        self.assertEqual(task_2.milestone_id, self.milestone_pigs)

        self.task_1.milestone_id = extra_milestone_pigs
        self.assertEqual(task_2.milestone_id, self.milestone_pigs)
        self.assertFalse(task_3.milestone_id,
                         "The milestone of the parent task should be set to its (grand)child tasks recursively. If a child task milestone should not be updated, it stops the recursion.")

        # F. Update of the parent's milestone, trigger the update of the subtask's milestone if they were the same before change
        self.task_1.milestone_id = self.milestone_pigs
        self.assertEqual(task_2.milestone_id, self.milestone_pigs)
        self.assertEqual(self.task_1.milestone_id, self.milestone_pigs)
        self.task_1.milestone_id = extra_milestone_pigs
        self.assertEqual(task_2.milestone_id, extra_milestone_pigs,
                         "If parent and child tasks share the same milestone, the update of the parent's milestone should trigger the update of its child's milestone.")

        # G. Same as F but project and milestone of the parent task are changed at the same time -> The milestone of the child change as it will follow its parent in the other project
        self.assertEqual(task_2.milestone_id, extra_milestone_pigs)
        self.assertEqual(self.task_1.milestone_id, extra_milestone_pigs)

        self.task_1.write({
            'project_id': self.project_goats.id,
            'milestone_id': self.milestone_goats.id,
        })
        self.assertTrue(
            task_2.milestone_id == self.task_1.milestone_id == self.milestone_goats,
            "The child milestone should be updated if the parent task's project is changed.",
        )

        # H. Same as G but project the project writen value is the same as the previous one -> No actual change of project_id so update the subtask milestone
        self.task_1.project_id = self.project_pigs
        task_2._compute_milestone_id()  # For some reason, though it should be auto triggered, because task_2.project_id changes with previous line, it's not
        self.task_1.milestone_id = extra_milestone_pigs
        self.assertEqual(task_2.milestone_id, extra_milestone_pigs)
        self.assertEqual(self.task_1.milestone_id, extra_milestone_pigs)

        self.task_1.write({
            'project_id': self.project_pigs.id,
            'milestone_id': self.milestone_pigs.id,
        })
        self.assertEqual(self.task_1.milestone_id, self.milestone_pigs)
        self.assertEqual(task_2.milestone_id, self.milestone_pigs,
                         "The child milestone should be updated as the project of the parent task does not actually change.")

        # I. Same case as G but the display_on_project is set to False on the child task -> Both project and milestone of the subtask should be updated
        self.task_1.write({
            'project_id': self.project_pigs.id,
            'milestone_id': extra_milestone_pigs.id,
        })
        self.assertEqual(task_2.milestone_id, extra_milestone_pigs)
        self.assertEqual(self.task_1.milestone_id, extra_milestone_pigs)

        self.task_1.write({
            'project_id': self.project_goats.id,
            'milestone_id': self.milestone_goats.id,
        })
        self.assertEqual(self.task_1.milestone_id, self.milestone_goats)
        self.assertEqual(task_2.project_id, self.project_goats)
        self.assertEqual(task_2.milestone_id, self.milestone_goats,
                         "The child milestone should be updated if the parent task's project is changed only if dislay_on_project is set to False for the subtask.")

        # J. Same case as F but subtask is closed -> no update of its milestone
        self.task_1.project_id = task_2.project_id = self.project_pigs
        self.task_1.milestone_id = task_2.milestone_id = self.milestone_pigs
        task_2.state = '1_done'
        self.assertEqual(task_2.milestone_id, self.milestone_pigs)
        self.assertEqual(self.task_1.milestone_id, self.milestone_pigs)

        self.task_1.write({
            'milestone_id': extra_milestone_pigs.id,
        })
        self.assertEqual(self.task_1.milestone_id, extra_milestone_pigs)
        self.assertEqual(task_2.milestone_id, self.milestone_pigs,
                         "The child milestone should not be updated if it is closed.")

    def test_project_milestone_color(self):
        """
        Test Steps:
        1. Assign `milestone_pigs` to `task_1` and mark it as 'done'.
        2. Set `milestone_goats` deadline to yesterday.
        3. Compute the next milestone for `project_pigs` and `project_goats`.
        4. Validate that:
           - `project_goats` has exceeded the milestone deadline.
           - `project_pigs` has not exceeded the milestone deadline.
           - `project_pigs` can mark the milestone as done.
           - `project_goats` cannot mark the milestone as done.
        """
        self.task_1.write({
            'milestone_id': self.milestone_pigs.id,
            'state': '1_done',
        })
        self.milestone_goats.write({'deadline': fields.Date.today() + relativedelta(days=-1)})

        (self.project_pigs | self.project_goats)._compute_next_milestone_id()

        self.assertTrue(self.project_goats.is_milestone_deadline_exceeded, "Expected project_goats to have exceeded the milestone deadline.")
        self.assertFalse(self.project_pigs.is_milestone_deadline_exceeded, "Expected project_pigs to not have exceeded the milestone deadline.")
        self.assertTrue(self.project_pigs.can_mark_milestone_as_done, "Expected project_pigs to be able to mark the milestone as done.")
        self.assertFalse(self.project_goats.can_mark_milestone_as_done, "Expected project_goats to not be able to mark the milestone as done.")
