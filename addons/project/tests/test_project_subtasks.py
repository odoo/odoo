# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
from lxml import etree

from odoo import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import Form, tagged
from odoo.tools import mute_logger
from odoo.exceptions import ValidationError


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
                - Should have a project set
                - Shouldn't be displayed
            2) Set project on subtask
                - Should not change parent project
                - Project should be correct
                - Should be displayed
            3) Reset the project to False
                - Should raise an error
            3bis) Reset the parent task project to False
                - Should raise an error
            4) Set project on parent to same project as subtask
                - Project should be correct
                - Shouldn't change subtask's display
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

        self.assertEqual(self.task_1.child_ids.project_id, self.task_1.project_id, "The project should be inheritted from parent.")
        self.assertFalse(self.task_1.child_ids.display_in_project, "By default, subtasks shouldn't be displayed in project.")

        # 2)
        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.edit(0) as child_task_form:
                child_task_form.project_id = self.project_goats
        self.assertEqual(self.task_1.project_id, self.project_pigs, "Changing the project of a subtask should not change parent project")
        self.assertEqual(self.task_1.child_ids.project_id, self.project_goats, "Display Project of the task should be well assigned")
        self.assertTrue(self.task_1.child_ids.display_in_project, "As the subtask isn't in the same project as its parent, it should be displayed")

        # 3)
        task_form = Form(self.task_1.with_context({'tracking_disable': True}))
        with task_form.child_ids.edit(0) as child_task_form:
            child_task_form.project_id = self.env['project.project']
        with self.assertRaises(psycopg2.errors.CheckViolation), mute_logger('odoo.sql_db'):
            task_form.save()

        # 3bis)
        task_form = Form(self.task_1.with_context({'tracking_disable': True}))
        task_form.project_id = self.env['project.project']
        with self.assertRaises(ValidationError), self.cr.savepoint():
            task_form.save()

        # 4)
        with Form(self.task_1.with_context({'tracking_disable': True})) as task_form:
            task_form.project_id = self.task_1.child_ids.project_id
        self.assertEqual(self.task_1.project_id, self.project_goats, "Parent project should change.")
        self.assertEqual(self.task_1.child_ids.project_id, self.project_goats, "Parent project should change.")
        self.assertTrue(self.task_1.child_ids.display_in_project, "Changing the project of the task shouldn't change de value of display_in_project of its subtask")

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

        self.assertEqual(self.task_1.child_ids.stage_id, stage_a, "Stage should be set on the subtask since it inheritted the project of its parent.")
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
                Command.create({'name': 'child 1', 'project_id': self.project_goats.id}),
                Command.create({'name': 'child 2', 'project_id': self.project_goats.id, 'display_in_project': True}),
                Command.create({'name': 'child 3', 'project_id': self.project_pigs.id, 'display_in_project': True}),
                Command.create({
                    'name': 'child 4 with subtask',
                    'project_id': self.project_goats.id,
                    'child_ids': [
                        Command.create({'name': 'child 5', 'project_id': self.project_goats.id}),
                        Command.create({'name': 'child 6 with project', 'project_id': self.project_goats.id, 'display_in_project': True})
                    ]}),
                Command.create({'name': 'child archived', 'project_id': self.project_goats.id, 'active': False}),
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
            6) verify if there is a copy in the subtask name.
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
                self.assertEqual(child_subtask_form.project_id, subtask_form.project_id)
                self.assertFalse(child_subtask_form.display_in_project)

        self.assertEqual(task.subtask_count, 1, "Parent task should have 1 children")
        task_2 = task.copy()
        self.assertEqual(task_2.subtask_count, 1, "If the parent task is duplicated then the sub task should be copied")
        self.assertEqual(task_2.child_ids[0].name, "Test Subtask 1 (copy)", "The name of the subtask should contain the word 'copy'.")

    def test_subtask_copy_display_in_project(self):
        """
            Check if `display_in_project` of subtask is not set to `True` during copy
        """
        project = self.env['project.project'].create({
            'name': 'Project',
        })
        task_A, task_B = self.env['project.task'].create([
            {
                'name': 'Task A',
                'project_id': project.id,
                'display_in_project': True,
            },
            {
                'name': 'Task B',
                'project_id': project.id,
                'display_in_project': True,
            },
        ])
        self.env['project.task'].create([
            {
                'name': 'Subtask A 1',
                'parent_id': task_A.id,
                'project_id': project.id,
            },
            {
                'name': 'Subtask A 2',
                'parent_id': task_A.id,
                'project_id': project.id,
            },
            {
                'name': 'Subtask B 1',
                'parent_id': task_B.id,
                'project_id': project.id,
            },
            {
                'name': 'Subtask B 2',
                'parent_id': task_B.id,
                'project_id': project.id,
            }
        ])
        subtask_not_display_in_project = project.task_ids.child_ids.filtered(lambda t: not t.display_in_project)
        self.assertEqual(len(subtask_not_display_in_project), 4, "No subtask should be displayed in the project")
        project_copy = project.copy()
        self.assertEqual(len(project_copy.task_ids.child_ids), 4)
        subtask_not_display_in_project_copy = project_copy.task_ids.child_ids.filtered(lambda t: not t.display_in_project)
        self.assertEqual(len(subtask_not_display_in_project_copy), 4, "No subtask should be displayed in the duplicate project")

    def test_subtask_copy_name(self):
        """ This test ensure that the name of task and project have the '(copy)' added to their name when needed.
            If a project is copied, the project's name should contain the 'copy' but the project's task should keep the same name as their original.
            If a task is copied (alone or in a recordset), its name as well as the name of its children should contain the 'copy'.
        """
        project = self.env['project.project'].create({
            'name': 'Project',
        })
        task_A = self.env['project.task'].create({
            'name': 'Task A',
            'project_id': project.id,
            'display_in_project': True,
            'child_ids': [Command.create({
                'name': 'Subtask A 1',
                'project_id': project.id,
                'child_ids': [Command.create({
                    'name': 'Sub Subtask A 1',
                    'project_id': project.id,
                })]
            }), Command.create({
                'name': 'Subtask A 2',
                'project_id': project.id,
            })]
        })
        project_copied = project.copy()
        self.assertEqual(project_copied.name, 'Project (copy)', 'The name of the project should contains the extra (copy).')
        parent_task = self.env['project.task'].search([('project_id', '=', project_copied.id), ('parent_id', '=', False)])
        self.assertEqual(parent_task.name, 'Task A', 'The task is copied from project.copy(). Its name should be the same.')
        self.assertEqual(parent_task.child_ids[0].name, 'Subtask A 1', 'The task is copied from project.copy(). Its name should be the same.')
        self.assertEqual(parent_task.child_ids[1].name, 'Subtask A 2', 'The task is copied from project.copy(). Its name should be the same.')
        self.assertEqual(parent_task.child_ids[0].child_ids.name, 'Sub Subtask A 1', 'The task is copied from project.copy(). Its name should be the same.')
        copied_task = task_A.copy()
        self.assertEqual(copied_task.name, 'Task A (copy)', 'The task is copied from task.copy(). Its name should contain the extra (copy).')
        self.assertEqual(copied_task.child_ids[0].name, 'Subtask A 1 (copy)', 'The task is copied from task.copy(). Its name should contain the extra (copy).')
        self.assertEqual(copied_task.child_ids[1].name, 'Subtask A 2 (copy)', 'The task is copied from task.copy(). Its name should contain the extra (copy).')
        self.assertEqual(copied_task.child_ids[0].child_ids.name, 'Sub Subtask A 1 (copy)', 'The task is copied from task.copy(). Its name should contain the extra (copy).')

    def test_subtask_unlinking(self):
        task_form = Form(self.task_1.with_context({'tracking_disable': True}))
        with task_form.child_ids.new() as child_task_form:
            child_task_form.name = 'Test Subtask 1'
            child_task_form.project_id = task_form.project_id
        task_form.save()
        child_subtask = self.task_1.child_ids[0]
        self.task_1.unlink()

        self.assertFalse(self.task_1.exists())
        self.assertFalse(child_subtask.exists(), 'Subtask should be removed if the parent task has been deleted')

    def test_get_all_subtasks(self):
        subsubtasks = self.env['project.task'].create([{
            'name': 'Subsubtask 1',
            'project_id': self.project_pigs.id,
        }, {
            'name': 'Subsubtask 2',
            'project_id': self.project_goats.id,
        }, {
            'name': 'Subsubtask 3',
            'project_id': self.project_pigs.id,
        }])
        subtasks = self.env['project.task'].create([{
            'name': 'Subtask 1',
            'project_id': self.project_pigs.id,
            'child_ids': subsubtasks[:2],
        }, {
            'name': 'Subtask 2',
            'project_id': self.project_goats.id,
            'child_ids': subsubtasks[2],
        }])
        task = self.env['project.task'].create({
            'name': 'Task 1',
            'project_id': self.project_goats.id,
            'child_ids': subtasks,
        })

        all_subtasks = task._get_all_subtasks()
        self.assertEqual(all_subtasks, subtasks | subsubtasks)

        all_subtasks_by_task_id = task._get_subtask_ids_per_task_id()
        self.assertEqual(len(all_subtasks_by_task_id), 1, "The result should only contain one item: the common ancestor")
        for parent_id, subtask_ids in all_subtasks_by_task_id.items():
            self.assertEqual(parent_id, task.id, "The key should be the common ancestor")
            self.assertEqual(set(subtask_ids), set(all_subtasks.ids),
                             "All subtasks linked to the common ancestor should be returned by _get_subtask_ids_per_task_id method")

    def test_subtask_copy_followers(self):
        """ This test will check that a task will propagate its followers to its subtasks """
        task_form = Form(self.task_1.with_context({'tracking_disable': True}))
        with task_form.child_ids.new() as child_task_form:
            child_task_form.name = 'Child Task'
            child_task_form.project_id = task_form.project_id
        task = task_form.save()
        self.assertEqual(task.message_follower_ids.mapped('email'), task.child_ids[0].message_follower_ids.mapped('email'), "The parent and child message_follower_ids should have the same emails")

    def test_subtask_is_visible_after_archiving(self):
        """
            Check if `display_in_project` of subtask is set to `True` once the subtask is archived
        """
        subtask = self.env['project.task'].create({
            'name': 'Subtask',
            'parent_id': self.task_1.id,
            'project_id': self.project_pigs.id,
        })
        self.assertFalse(subtask.display_in_project)
        subtask.action_archive()
        self.assertTrue(subtask.display_in_project)

    def test_toggle_active_task_with_subtasks(self):
        """ This test will check archiving task should archive it's subtasks and vice versa"""

        parent_task = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Parent Task',
            'project_id': self.project_goats.id,
        })
        child_1, child_2, child_3, child_4 = self.env['project.task'].with_context({'mail_create_nolog': True}).create([
            {
                'name': 'child 1',
                'project_id': self.project_goats.id,
                'parent_id': parent_task.id,
                'child_ids': [
                    Command.create({
                        'name': 'Child 1 (Subtask 1)',
                        'project_id': self.project_goats.id,
                    }),
                    Command.create({
                        'name': 'Child 1 (Subtask 2)',
                        'project_id': self.project_goats.id,
                        'child_ids': [Command.create({
                            'name': 'Subsubtask',
                            'project_id': self.project_goats.id,
                        })],
                    }),
                ],
            },
            {
                'name': 'child 2',
                'project_id': self.project_goats.id,
                'parent_id': parent_task.id,
            },
            {
                'name': 'child 3',
                'parent_id': parent_task.id,
                'project_id': self.project_goats.id,
                'display_in_project': True,
                'child_ids': [
                    Command.create({
                        'name': 'Child 3 (Subtask 1)',
                        'project_id': self.project_goats.id,
                    }),
                    Command.create({
                        'name': 'Child 3 (Subtask 2)',
                        'project_id': self.project_goats.id,
                    }),
                ],
            },
            {
                'name': 'child 4',
                'parent_id': parent_task.id,
                'project_id': self.project_goats.id,
                'display_in_project': True,
            },
        ])
        self.assertEqual(9, len(parent_task._get_all_subtasks()), "Should have 9 subtasks")
        parent_task.action_archive()
        self.assertFalse(all((parent_task + child_1._get_all_subtasks() + child_2).mapped('active')),
            "Parent, `child 1` task (with its descendant tasks) and `Child 2` task should be archived")
        self.assertTrue(all(child_3._get_all_subtasks().mapped('active')), "`child 3` task and its descendant tasks should be unarchived")
        self.assertEqual(2, len(parent_task.child_ids), "Should have 2 direct non archived subtasks")
        self.assertEqual(parent_task.child_ids, child_3 + child_4, "Should have 2 direct non archived subtasks")
        self.assertEqual(4, len(parent_task._get_all_subtasks().filtered('active')), "Should have 4 non archived subtasks")

    def test_write_project_should_propagate_to_no_display_subtasks(self):
        task = self.env['project.task'].create({
            'name': 'Task visible',
            'project_id': self.project_goats.id,
            'child_ids': [
                Command.create({
                    'name': 'Sub-task invisible',
                    'project_id': self.project_goats.id,
                }),
                Command.create({
                    'name': 'Sub-task visible',
                    'project_id': self.project_goats.id,
                    'display_in_project': True,
                }),
            ],
        })
        invisible, visible = task.child_ids
        self.assertFalse(invisible.display_in_project)
        self.assertTrue(visible.display_in_project)

        task.project_id = self.project_pigs
        self.assertEqual(invisible.project_id, self.project_pigs, "Project should be propagated to invisible subtask")
        self.assertEqual(visible.project_id, self.project_goats, "Project shouldn't be propagated to visible subtask")

    def test_display_in_project_unset_parent(self):
        """ Test _onchange_parent_id when there is no parent task
        """
        Task = self.env['project.task']
        task = Task.create({
            'name': 'Task',
            'parent_id': self.task_1.id,
            'project_id': self.task_1.project_id.id,
        })
        view = self.env.ref('project.view_task_form2')
        tree = etree.fromstring(view.arch)
        for node in tree.xpath('//field[@name="parent_id"][@invisible]'):
            node.attrib.pop('invisible')
        view.arch = etree.tostring(tree)
        with Form(task) as task_form:
            task_form.parent_id = Task
        self.assertEqual(task.project_id, self.task_1.project_id, "project_id should be affected")
        self.assertTrue(task.display_in_project, "display_in_project should be True when there is no parent task")
