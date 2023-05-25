# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import tagged
from odoo.tests.common import Form

@tagged('-at_install', 'post_install')
class TestProjectSubtasks(TestProjectCommon):

    def test_task_display_project_with_default_form(self):
        """
            Create a task in the default task form should take the project set in the form or the default project in the context
        """
        with Form(self.env['project.task'].with_context({'tracking_disable': True})) as task_form:
            task_form.name = 'Test Task 1'
            task_form.project_id = self.project_pigs
        task = task_form.save()

        self.assertEqual(task.project_id, self.project_pigs, "The project should be assigned.")

        with Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_pigs.id})) as task_form:
            task_form.name = 'Test Task 2'
        task = task_form.save()

        self.assertEqual(task.project_id, self.project_pigs, "The project should be assigned from the default project.")

    def test_task_display_project_with_task_form2(self):
        """
            Create a task in the task form 2 should take the project set in the form or the default project in the context
        """
        with Form(self.env['project.task'].with_context({'tracking_disable': True}), view="project.view_task_form2") as task_form:
            task_form.name = 'Test Task 1'
            task_form.project_id = self.project_pigs
        task = task_form.save()

        self.assertEqual(task.project_id, self.project_pigs, "The project should be assigned.")

        with Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_pigs.id}), view="project.view_task_form2") as task_form:
            task_form.name = 'Test Task 2'
        task = task_form.save()

        self.assertEqual(task.project_id, self.project_pigs, "The project should be assigned from the default project.")

    def test_task_display_project_with_quick_create_task_form(self):
        """
            Create a task in the quick create form should take the default project in the context
        """
        task_form = Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_pigs.id}), view="project.quick_create_task_form")
        task_form.display_name = 'Test Task 2'
        task = task_form.save()

        self.assertEqual(task.project_id, self.project_pigs, "The project should be assigned from the default project.")

    def test_task_display_project_with_any_task_form(self):
        """
            Create a task in any form should take the default project in the context
        """
        form_views = self.env['ir.ui.view'].search([('model', '=', 'project.task'), ('type', '=', 'form')])
        for form_view in form_views:
            task_form = Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_pigs.id, 'default_name': 'Test Task 1', 'default_display_name': 'Test Task 1'}), view=form_view)
            # Some views have the `name` field invisible
            # As the goal is simply to test the default project field and not the name, we can skip setting the name
            # in the view and set it using `default_name` instead
            # Quick create form use display_name and for the same goal, we can add default_display_name for that form
            task = task_form.save()

            self.assertEqual(task.project_id, self.project_pigs, "The project should be assigned from the default project, form_view name : %s." % form_view.name)

    def test_subtask_project(self):
        """
            1) Create a subtask
                - Shouldn't have a project set.
            2) Set project on subtask
                - Should not change parent project
                - Project should be correct
            3) Reset the project to False
                - Project should be correct
            4) Change parent task project
                - Project should stay false
            5) Set project on subtask and change parent task project
                - Project should be the one set by the user
            6) Remove parent task:
                - The project id should remain unchanged
            7) Remove project id then parent id:
                - Project should be removed
                - Parent should be removed
        """
        # 1)
        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.new() as child_task_form:
                child_task_form.name = 'Test Subtask 1'

        self.assertFalse(self.task_1.child_ids.project_id, "The project should be False by default.")

        # 2)
        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.edit(0) as child_task_form:
                child_task_form.project_id = self.project_goats
        self.assertEqual(self.task_1.project_id, self.project_pigs, "Changing the project of a subtask should not change parent project")
        self.assertEqual(self.task_1.child_ids.project_id, self.project_goats, "Display Project of the task should be well assigned")
        self.assertEqual(self.task_1.child_ids.project_id, self.project_goats, "Changing display project id on a subtask should change project id")

        # 3)
        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.edit(0) as child_task_form:
                child_task_form.project_id = self.env['project.project']

        self.assertFalse(self.task_1.child_ids.project_id, "The project of the subtask should be False")

        # 4)
        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            task_form.project_id = self.project_goats

        self.assertEqual(self.task_1.project_id, self.project_goats, "Parent project should change.")
        self.assertFalse(self.task_1.child_ids.project_id, "The project of the subtask should stay False")

        # 5)
        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.edit(0) as child_task_form:
                child_task_form.project_id = self.project_goats
            task_form.project_id = self.project_pigs

        self.assertEqual(self.task_1.project_id, self.project_pigs, "Parent project should change back.")
        self.assertEqual(self.task_1.child_ids.project_id, self.project_goats, "The project of the subtask should have the one set by the user")

        # Debug mode required for `parent_id` to be visible in the view
        with self.debug_mode():
            # 6)
            with Form(self.task_1.child_ids.with_context({'tracking_disable': True})) as subtask_form:
                subtask_form.parent_id = self.env['project.task']
            orphan_subtask = subtask_form.save()

            self.assertEqual(orphan_subtask.project_id, self.project_goats, "The project of the orphan task should stay the same even if it no longer has a parent task")
            self.assertFalse(orphan_subtask.parent_id, "Parent should be false")

            # 7)
            with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
                with task_form.child_ids.new() as child_task_form:
                    child_task_form.name = 'Test Subtask 1'
                    child_task_form.project_id = self.project_goats
            with Form(self.task_1.child_ids.with_context({'tracking_disable': True})) as subtask_form:
                subtask_form.project_id = self.env['project.project']
                subtask_form.parent_id = self.env['project.task']
            orphan_subtask = subtask_form.save()

            self.assertFalse(orphan_subtask.project_id, "The project should be removed as expected.")
            self.assertFalse(orphan_subtask.project_id, "The Parent should be removed as expected.")

    def test_subtask_stage(self):
        """
            The stage of the new child must be the default one of the project
        """
        stage_a = self.env['project.task.type'].create({'name': 'a', 'sequence': 1})
        stage_b = self.env['project.task.type'].create({'name': 'b', 'sequence': 10})
        self.project_pigs.type_ids |= stage_a
        self.project_pigs.type_ids |= stage_b

        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.new() as child_task_form:
                child_task_form.name = 'Test Subtask 1'

        self.assertFalse(self.task_1.child_ids.stage_id, "No stage should be set on the subtask since no project is set by default.")
        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.edit(0) as subtask_form:
                subtask_form.project_id = task_form.project_id

        self.assertEqual(self.task_1.child_ids.stage_id, stage_a, "The stage of the child task should be the default one of the project.")

        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            task_form.stage_id = stage_b

        self.assertEqual(self.task_1.child_ids.stage_id, stage_a, "The stage of the child task should remain the same while changing parent task stage.")

        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            task_form.child_ids.remove(index=0)
            with task_form.child_ids.new() as child_task_form:
                child_task_form.name = 'Test Subtask 2'
                child_task_form.project_id = task_form.project_id

        self.assertEqual(self.task_1.child_ids.stage_id, stage_a, "The stage of the child task should be the default one of the project even if parent stage id is different.")

        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.edit(0) as child_task_form:
                child_task_form.project_id = self.project_goats

        self.assertEqual(self.task_1.child_ids.stage_id.name, "New", "The stage of the child task should be the default one of the display project id, once set.")

    def test_copy_project_with_subtasks(self):
        self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Parent Task',
            'project_id': self.project_goats.id,
            'child_ids': [
                Command.create({'name': 'child 1'}),
                Command.create({'name': 'child 2', 'project_id': self.project_goats.id}),
                Command.create({'name': 'child 3', 'project_id': self.project_pigs.id}),
                Command.create({'name': 'child 4 with subtask', 'child_ids': [Command.create({'name': 'child 5'}), Command.create({'name': 'child 6 with project', 'project_id': self.project_goats.id})]}),
                Command.create({'name': 'child archived', 'active': False}),
            ],
        })

        task_count_with_subtasks_including_archived = 8
        task_count_in_project_pigs = self.project_pigs.task_count
        self.project_goats._compute_task_count()  # recompute without archived tasks and subtasks
        task_count_in_project_goats = self.project_goats.task_count
        project_goats_duplicated = self.project_goats.copy()
        self.project_pigs._compute_task_count()  # retrigger since a new task should be added in the project after the duplication of Project Goats

        def dfs(task):
            # ABGH: i used dfs to avoid visiting a task 2 times as it can be a direct task for the project and a subtask for another task like child 6
            visited[task.id] = True
            total_count = 1
            for child_id in task.child_ids:
                if child_id.id not in visited:
                    total_count += dfs(child_id)
            return total_count

        visited = {}
        tasks_copied_count = 0
        for task in project_goats_duplicated.tasks:
            if not task.id in visited:
                tasks_copied_count += dfs(task)

        self.assertEqual(
            tasks_copied_count,
            task_count_with_subtasks_including_archived - 1,
            'The number of duplicated tasks (subtasks included) should be equal to the number of all tasks (with active subtasks included) of both projects, '
            'that is only the active subtasks are duplicated.')
        self.assertEqual(self.project_goats.task_count, task_count_in_project_goats, 'The number of tasks should be the same before and after the duplication of this project.')
        self.assertEqual(self.project_pigs.task_count, task_count_in_project_pigs + 1, 'The project pigs should an additional task after the duplication of the project goats.')

    def test_subtask_creation_with_form(self):
        """
            1) test the creation of sub-tasks through the notebook
            2) set a parent task on an existing task
            3) test the creation of sub-sub-tasks
            4) check the correct nb of sub-tasks is displayed in the 'sub-tasks' stat button and on the parent task kanban card
            5) sub-tasks should be copied when the parent task is duplicated
        """

        task_form = Form(self.task_1.with_context({'tracking_disable': True}))
        with task_form.child_ids.new() as child_task_form:
            child_task_form.name = 'Test Subtask 1'
            child_task_form.project_id = task_form.project_id
        task = task_form.save()

        child_subtask = self.task_1.child_ids[0]

        with Form(child_subtask.with_context(tracking_disable=True)) as subtask_form:
            with subtask_form.child_ids.new() as child_subtask_form:
                child_subtask_form.name = 'Test Subtask 2'
                self.assertFalse(child_subtask_form.project_id)

        self.assertEqual(task.subtask_count, 1, "Parent task should have 1 children")
        task_2 = task.copy()
        self.assertEqual(task_2.subtask_count, 1, "If the parent task is duplicated then the sub task should be copied")

    def test_project_root_id(self):
        task = self.env['project.task'].create({
            'name': 'Task 1',
            'project_id': self.project_goats.id,
            'child_ids': [
                Command.create({
                    'name': 'Subtask 1',
                    'child_ids': [Command.create({'name': 'Subsubtask 1'})],
                }),
            ],
        })
        subtask = task.child_ids
        subsubtask = subtask.child_ids
        self.assertTrue(bool(subtask))
        self.assertTrue(bool(subsubtask))
        self.assertEqual(task.project_root_id, task.project_id)
        self.assertFalse(subtask.project_id)
        self.assertEqual(subtask.project_root_id, task.project_id)
        self.assertFalse(subsubtask.project_id)
        self.assertEqual(subsubtask.project_root_id, task.project_id)

        subtask.project_id = self.project_pigs
        self.assertNotEqual(subtask.project_root_id, task.project_id)
        self.assertEqual(subtask.project_root_id, self.project_pigs)
        self.assertFalse(subsubtask.project_id)
        self.assertNotEqual(subsubtask.project_root_id, task.project_id)
        self.assertEqual(subsubtask.project_root_id, subtask.project_id)

        subtask.project_id = False
        subsubtask.project_id = self.project_pigs
        self.assertEqual(subtask.project_root_id, task.project_id)
        self.assertNotEqual(subsubtask.project_root_id, task.project_id)
        self.assertEqual(subsubtask.project_root_id, self.project_pigs)
