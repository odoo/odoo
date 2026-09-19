from lxml import etree
from psycopg.errors import CheckViolation

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.project.tests.test_project_base import TestProjectCommon


@tagged("-at_install", "post_install")
class TestProjectSubtasks(TestProjectCommon):
    def test_task_display_project_with_default_form(self) -> None:
        with Form(
            self.env["project.task"].with_context({"tracking_disable": True})
        ) as task_form:
            task_form.name = "Test Task 1"
            task_form.project_id = self.project_pigs
        task = task_form.save()

        self.assertEqual(
            task.project_id,
            self.project_pigs,
            "The project should be assigned.",
        )

        with Form(
            self.env["project.task"].with_context(
                {
                    "tracking_disable": True,
                    "default_project_id": self.project_pigs.id,
                }
            )
        ) as task_form:
            task_form.name = "Test Task 2"
        task = task_form.save()

        self.assertEqual(
            task.project_id,
            self.project_pigs,
            "The project should be assigned from the default project.",
        )

    def test_task_display_project_with_task_form2(self) -> None:
        with Form(
            self.env["project.task"].with_context({"tracking_disable": True}),
            view="project.view_task_form2",
        ) as task_form:
            task_form.name = "Test Task 1"
            task_form.project_id = self.project_pigs
        task = task_form.save()

        self.assertEqual(
            task.project_id,
            self.project_pigs,
            "The project should be assigned.",
        )

        with Form(
            self.env["project.task"].with_context(
                {
                    "tracking_disable": True,
                    "default_project_id": self.project_pigs.id,
                }
            ),
            view="project.view_task_form2",
        ) as task_form:
            task_form.name = "Test Task 2"
        task = task_form.save()

        self.assertEqual(
            task.project_id,
            self.project_pigs,
            "The project should be assigned from the default project.",
        )

    def test_task_display_project_with_quick_create_task_form(self) -> None:
        task_form = Form(
            self.env["project.task"].with_context(
                {
                    "tracking_disable": True,
                    "default_project_id": self.project_pigs.id,
                }
            ),
            view="project.quick_create_task_form",
        )
        task_form.display_name = "Test Task 2"
        task = task_form.save()

        self.assertEqual(
            task.project_id,
            self.project_pigs,
            "The project should be assigned from the default project.",
        )

    def test_task_display_project_with_any_task_form(self) -> None:
        form_views = self.env["ir.ui.view"].search(
            [("model", "=", "project.task"), ("type", "=", "form")]
        )
        for form_view in form_views:
            task_form = Form(
                self.env["project.task"].with_context(
                    {
                        "tracking_disable": True,
                        "default_project_id": self.project_pigs.id,
                        "default_name": "Test Task 1",
                        "default_display_name": "Test Task 1",
                    }
                ),
                view=form_view,
            )
            task = task_form.save()

            self.assertEqual(
                task.project_id,
                self.project_pigs,
                "The project should be assigned from the default project, form_view name : %s."
                % form_view.name,
            )

    @mute_logger("odoo.db")
    def test_subtask_project(self) -> None:
        parent_task = self.task_1.with_context({"tracking_disable": True})

        child_task = parent_task.create(
            {
                "name": "Test Subtask 1",
                "parent_id": parent_task.id,
                "project_id": parent_task.project_id.id,
            }
        ).with_context({"tracking_disable": True})
        self.assertEqual(
            child_task.project_id,
            self.task_1.project_id,
            "The project should be inheritted from parent.",
        )
        self.assertFalse(
            child_task.display_in_project,
            "By default, subtasks shouldn't be displayed in project.",
        )

        child_task.project_id = self.project_goats
        self.assertEqual(
            self.task_1.project_id,
            self.project_pigs,
            "Changing the project of a subtask should not change parent project",
        )
        self.assertEqual(
            child_task.project_id,
            self.project_goats,
            "Display Project of the task should be well assigned",
        )
        self.assertTrue(
            child_task.display_in_project,
            "As the subtask isn't in the same project as its parent, it should be displayed",
        )

        with self.assertRaises(CheckViolation):
            child_task.project_id = False

        with self.assertRaises(ValidationError):
            parent_task.project_id = False

        parent_task.project_id = self.task_1.child_ids.project_id
        self.assertEqual(
            self.task_1.project_id,
            self.project_goats,
            "Parent project should change",
        )
        self.assertEqual(
            child_task.project_id,
            self.project_goats,
            "Child project should change",
        )
        self.assertTrue(
            child_task.display_in_project,
            "Changing the project of the task shouldn't change de value of display_in_project of its subtask",
        )

        parent_task.write(
            {
                "project_id": self.project_pigs.id,
                "child_ids": [
                    (
                        1,
                        parent_task.child_ids[0].id,
                        {"project_id": self.project_goats.id},
                    )
                ],
            }
        )

        self.assertEqual(
            self.task_1.project_id,
            self.project_pigs,
            "Parent project should change back",
        )
        self.assertEqual(
            child_task.project_id,
            self.project_goats,
            "The project of the subtask should have the one set by the user",
        )

        child_task.parent_id = False
        self.assertEqual(
            child_task.project_id,
            self.project_goats,
            "The project of the orphan task should stay the same even if it no longer has a parent task",
        )
        self.assertFalse(child_task.parent_id, "Parent should be false")

        other_child_task = parent_task.create(
            {
                "name": "Test Subtask 1",
                "parent_id": parent_task.id,
                "project_id": self.project_goats.id,
            }
        )
        other_child_task.write(
            {
                "project_id": False,
                "parent_id": False,
            }
        )
        self.assertFalse(
            other_child_task.project_id,
            "The project should be removed as expected",
        )
        self.assertFalse(
            other_child_task.parent_id,
            "The parent should be removed as expected",
        )

    def test_subtask_stage(self) -> None:
        parent_task = self.task_1.with_context({"tracking_disable": True})

        self.project_pigs.workflow_step_ids.sequence = 100
        stage_a = self.env["project.workflow.step"].create({"name": "a", "sequence": 1})
        stage_b = self.env["project.workflow.step"].create(
            {"name": "b", "sequence": 10}
        )
        self.project_pigs.workflow_step_ids |= stage_a
        self.project_pigs.workflow_step_ids |= stage_b

        child_task = parent_task.create(
            {
                "name": "Test Subtask 1",
                "parent_id": parent_task.id,
                "project_id": parent_task.project_id.id,
            }
        ).with_context({"tracking_disable": True})
        self.assertEqual(
            child_task.step_id,
            stage_a,
            "Stage should be set on the subtask since it inheritted the project of its parent.",
        )

        child_task.project_id = parent_task.project_id
        self.assertEqual(
            child_task.step_id,
            stage_a,
            "The stage of the child task should be the default one of the project.",
        )

        parent_task.step_id = stage_b
        self.assertEqual(
            child_task.step_id,
            stage_a,
            "The stage of the child task should remain the same while changing parent task stage.",
        )

        parent_task.child_ids = False
        other_child_task = parent_task.create(
            {
                "name": "Test Subtask 2",
                "parent_id": parent_task.id,
                "project_id": parent_task.project_id.id,
            }
        ).with_context({"tracking_disable": True})
        self.assertEqual(
            other_child_task.step_id,
            stage_a,
            "The stage of the child task should be the default one of the project even if parent stage id is different.",
        )

        other_child_task.project_id = self.project_goats
        self.assertEqual(
            other_child_task.step_id.name,
            "New",
            "The stage of the child task should be the default one of the display project id, once set.",
        )

    def test_copy_project_with_subtasks(self) -> None:
        self.env["project.task"].with_context({"mail_create_nolog": True}).create(
            {
                "name": "Parent Task",
                "project_id": self.project_goats.id,
                "child_ids": [
                    Command.create(
                        {"name": "child 1", "project_id": self.project_goats.id}
                    ),
                    Command.create(
                        {"name": "child 2", "project_id": self.project_pigs.id}
                    ),
                    Command.create(
                        {
                            "name": "child 3 with subtask",
                            "project_id": self.project_goats.id,
                            "child_ids": [
                                Command.create(
                                    {
                                        "name": "granchild 3.1",
                                        "project_id": self.project_goats.id,
                                    }
                                ),
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "child archived",
                            "project_id": self.project_goats.id,
                            "active": False,
                        }
                    ),
                ],
            }
        )

        task_count_with_subtasks_including_archived = 6
        task_count_in_project_pigs = self.project_pigs.task_count
        self.project_goats._compute_task_counts()
        task_count_in_project_goats = self.project_goats.task_count
        project_goats_duplicated = self.project_goats.copy()
        self.project_pigs._compute_task_counts()

        def dfs(task) -> None:
            visited[task.id] = True
            total_count = 1
            for child_id in task.child_ids:
                if child_id.id not in visited:
                    total_count += dfs(child_id)
            return total_count

        visited = {}
        tasks_copied_count = 0
        for task in project_goats_duplicated.task_ids:
            if task.id not in visited:
                tasks_copied_count += dfs(task)

        self.assertEqual(
            tasks_copied_count,
            task_count_with_subtasks_including_archived - 1,
            "The number of duplicated tasks (subtasks included) should be equal to the number of all tasks (with active subtasks included) of both projects, "
            "that is only the active subtasks are duplicated.",
        )
        self.assertEqual(
            self.project_goats.task_count,
            task_count_in_project_goats,
            "The number of tasks should be the same before and after the duplication of this project.",
        )
        self.assertEqual(
            self.project_pigs.task_count,
            task_count_in_project_pigs + 1,
            "The project pigs should an additional task after the duplication of the project goats.",
        )

    def test_subtask_creation_with_form(self) -> None:
        task_form = Form(self.task_1.with_context({"tracking_disable": True}))
        with task_form.child_ids.new() as child_task_form:
            child_task_form.name = "Test Subtask 1"
            child_task_form.project_id = task_form.project_id
        task = task_form.save()

        child_subtask = self.task_1.child_ids[0]

        with (
            Form(child_subtask.with_context(tracking_disable=True)) as subtask_form,
            subtask_form.child_ids.new() as child_subtask_form,
        ):
            child_subtask_form.name = "Test Subtask 2"
            self.assertEqual(child_subtask_form.project_id, subtask_form.project_id)
            self.assertFalse(child_subtask_form.display_in_project)

        self.assertEqual(task.subtask_count, 1, "Parent task should have 1 children")
        task_2 = task.copy()
        self.assertEqual(
            task_2.subtask_count,
            1,
            "If the parent task is duplicated then the sub task should be copied",
        )
        self.assertEqual(
            task_2.child_ids[0].name,
            "Test Subtask 1 (copy)",
            "The name of the subtask should contain the word 'copy'.",
        )

    def test_subtask_copy_display_in_project(self) -> None:
        project = self.env["project.project"].create(
            {
                "name": "Project",
            }
        )
        task_A, task_B = self.env["project.task"].create(
            [
                {
                    "name": "Task A",
                    "project_id": project.id,
                },
                {
                    "name": "Task B",
                    "project_id": project.id,
                },
            ]
        )
        self.env["project.task"].create(
            [
                {
                    "name": "Subtask A 1",
                    "parent_id": task_A.id,
                    "project_id": project.id,
                },
                {
                    "name": "Subtask A 2",
                    "parent_id": task_A.id,
                    "project_id": project.id,
                },
                {
                    "name": "Subtask B 1",
                    "parent_id": task_B.id,
                    "project_id": project.id,
                },
                {
                    "name": "Subtask B 2",
                    "parent_id": task_B.id,
                    "project_id": project.id,
                },
            ]
        )
        subtask_not_display_in_project = project.task_ids.child_ids.filtered(
            lambda t: not t.display_in_project
        )
        self.assertEqual(
            len(subtask_not_display_in_project),
            4,
            "No subtask should be displayed in the project",
        )
        project_copy = project.copy()
        self.assertEqual(len(project_copy.task_ids.child_ids), 4)
        subtask_not_display_in_project_copy = project_copy.task_ids.child_ids.filtered(
            lambda t: not t.display_in_project
        )
        self.assertEqual(
            len(subtask_not_display_in_project_copy),
            4,
            "No subtask should be displayed in the duplicate project",
        )

    def test_subtask_copy_name(self) -> None:
        project = self.env["project.project"].create(
            {
                "name": "Project",
            }
        )
        task_A = self.env["project.task"].create(
            {
                "name": "Task A",
                "project_id": project.id,
                "child_ids": [
                    Command.create(
                        {
                            "name": "Subtask A 1",
                            "project_id": project.id,
                            "child_ids": [
                                Command.create(
                                    {
                                        "name": "Sub Subtask A 1",
                                        "project_id": project.id,
                                    }
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "Subtask A 2",
                            "project_id": project.id,
                        }
                    ),
                ],
            }
        )
        project_copied = project.copy()
        self.assertEqual(
            project_copied.name,
            "Project (copy)",
            "The name of the project should contains the extra (copy).",
        )
        parent_task = self.env["project.task"].search(
            [("project_id", "=", project_copied.id), ("parent_id", "=", False)]
        )
        self.assertEqual(
            parent_task.name,
            "Task A",
            "The task is copied from project.copy(). Its name should be the same.",
        )
        self.assertEqual(
            parent_task.child_ids.mapped("name"),
            task_A.child_ids.mapped("name"),
            "The subtasks are copied in their order. Their names should be the same.",
        )
        self.assertEqual(
            parent_task.child_ids.filtered(
                lambda t: t.name == "Subtask A 1"
            ).child_ids.name,
            "Sub Subtask A 1",
            "The task is copied from project.copy(). Its name should be the same.",
        )
        copied_task = task_A.copy()
        self.assertEqual(
            copied_task.name,
            "Task A (copy)",
            "The task is copied from task.copy(). Its name should contain the extra (copy).",
        )
        self.assertEqual(
            copied_task.child_ids.mapped("name"),
            [f"{name} (copy)" for name in task_A.child_ids.mapped("name")],
            "The task is copied from task.copy(). Its name should contain the extra (copy).",
        )
        self.assertEqual(
            copied_task.child_ids.filtered(
                lambda t: t.name == "Subtask A 1 (copy)"
            ).child_ids.name,
            "Sub Subtask A 1 (copy)",
            "The task is copied from task.copy(). Its name should contain the extra (copy).",
        )

    def test_subtask_unlinking(self) -> None:
        task_form = Form(self.task_1.with_context({"tracking_disable": True}))
        with task_form.child_ids.new() as child_task_form:
            child_task_form.name = "Test Subtask 1"
            child_task_form.project_id = task_form.project_id
        task_form.save()
        child_subtask = self.task_1.child_ids[0]
        self.task_1.unlink()

        self.assertFalse(self.task_1.exists())
        self.assertFalse(
            child_subtask.exists(),
            "Subtask should be removed if the parent task has been deleted",
        )

    def test_get_all_subtasks(self) -> None:
        subsubtasks = self.env["project.task"].create(
            [
                {
                    "name": "Subsubtask 1",
                    "project_id": self.project_pigs.id,
                },
                {
                    "name": "Subsubtask 2",
                    "project_id": self.project_goats.id,
                },
                {
                    "name": "Subsubtask 3",
                    "project_id": self.project_pigs.id,
                },
            ]
        )
        subtasks = self.env["project.task"].create(
            [
                {
                    "name": "Subtask 1",
                    "project_id": self.project_pigs.id,
                    "child_ids": subsubtasks[:2],
                },
                {
                    "name": "Subtask 2",
                    "project_id": self.project_goats.id,
                    "child_ids": subsubtasks[2],
                },
            ]
        )
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project_goats.id,
                "child_ids": subtasks,
            }
        )

        all_subtasks = task._get_all_subtasks()
        self.assertEqual(all_subtasks, subtasks | subsubtasks)

        all_subtasks_by_task_id = task._get_subtask_ids_per_task_id()
        self.assertEqual(
            len(all_subtasks_by_task_id),
            1,
            "The result should only contain one item: the common ancestor",
        )
        for parent_id, subtask_ids in all_subtasks_by_task_id.items():
            self.assertEqual(
                parent_id, task.id, "The key should be the common ancestor"
            )
            self.assertEqual(
                set(subtask_ids),
                set(all_subtasks.ids),
                "All subtasks linked to the common ancestor should be returned by _get_subtask_ids_per_task_id method",
            )

    def test_subtask_copy_followers(self) -> None:
        task_form = Form(self.task_1.with_context({"tracking_disable": True}))
        with task_form.child_ids.new() as child_task_form:
            child_task_form.name = "Child Task"
            child_task_form.project_id = task_form.project_id
        task = task_form.save()
        self.assertEqual(
            task.message_follower_ids.mapped("partner_id.email"),
            task.child_ids[0].message_follower_ids.mapped("partner_id.email"),
            "The parent and child message_follower_ids should have the same emails",
        )

    def test_toggle_active_task_with_subtasks(self) -> None:
        parent_task = (
            self.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Parent Task",
                    "project_id": self.project_goats.id,
                    "child_ids": [
                        Command.create(
                            {
                                "name": "child 1",
                                "project_id": self.project_goats.id,
                                "child_ids": [
                                    Command.create(
                                        {
                                            "name": "Child 1 (Subtask 1)",
                                            "project_id": self.project_goats.id,
                                        }
                                    ),
                                    Command.create(
                                        {
                                            "name": "Child 1 (Subtask 2)",
                                            "project_id": self.project_goats.id,
                                            "child_ids": [
                                                Command.create(
                                                    {
                                                        "name": "Subsubtask",
                                                        "project_id": self.project_goats.id,
                                                    }
                                                )
                                            ],
                                        }
                                    ),
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "name": "child 2",
                                "project_id": self.project_goats.id,
                            }
                        ),
                        Command.create(
                            {
                                "name": "child 3",
                                "project_id": self.project_pigs.id,
                                "child_ids": [
                                    Command.create(
                                        {
                                            "name": "Child 3 (Subtask 1)",
                                            "project_id": self.project_pigs.id,
                                        }
                                    ),
                                    Command.create(
                                        {
                                            "name": "Child 3 (Subtask 2)",
                                            "project_id": self.project_pigs.id,
                                        }
                                    ),
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "name": "child 4",
                                "project_id": self.project_pigs.id,
                            }
                        ),
                    ],
                }
            )
        )
        child_1 = parent_task.child_ids.filtered(lambda c: c.name == "child 1")
        child_2 = parent_task.child_ids.filtered(lambda c: c.name == "child 2")
        child_3 = parent_task.child_ids.filtered(lambda c: c.name == "child 3")
        child_4 = parent_task.child_ids.filtered(lambda c: c.name == "child 4")
        self.assertEqual(
            9, len(parent_task._get_all_subtasks()), "Should have 9 subtasks"
        )
        parent_task.action_archive()
        self.assertFalse(
            all((parent_task + child_1._get_all_subtasks() + child_2).mapped("active")),
            "Parent, `child 1` task (with its descendant tasks) and `Child 2` task should be archived",
        )
        self.assertTrue(
            all(child_3._get_all_subtasks().mapped("active")),
            "`child 3` task and its descendant tasks should be unarchived",
        )
        self.assertEqual(
            2,
            len(parent_task.child_ids),
            "Should have 2 direct non archived subtasks",
        )
        self.assertEqual(
            parent_task.child_ids,
            child_3 + child_4,
            "Should have 2 direct non archived subtasks",
        )
        self.assertEqual(
            4,
            len(parent_task._get_all_subtasks().filtered("active")),
            "Should have 4 non archived subtasks",
        )

    def test_display_in_project_unset_parent(self) -> None:
        Task = self.env["project.task"]
        task = Task.create(
            {
                "name": "Task",
                "parent_id": self.task_1.id,
                "project_id": self.task_1.project_id.id,
            }
        )
        view = self.env.ref("project.view_task_form2")
        tree = etree.fromstring(view.arch)
        for node in tree.xpath('//field[@name="parent_id"][@invisible]'):
            node.attrib.pop("invisible")
        view.arch = etree.tostring(tree)
        with Form(task) as task_form:
            task_form.parent_id = Task
        task._compute_display_in_project()
        self.assertEqual(
            task.project_id,
            self.task_1.project_id,
            "project_id should be affected",
        )
        self.assertTrue(
            task.display_in_project,
            "display_in_project should be True when there is no parent task",
        )

    def test_invisible_subtask_became_visible_when_converted_to_task(
        self,
    ) -> None:
        task = self.env["project.task"].create(
            {
                "name": "Parent task",
                "project_id": self.project_goats.id,
                "child_ids": [
                    Command.create(
                        {
                            "name": "Sub-task invisible",
                            "project_id": self.project_goats.id,
                        }
                    )
                ],
            }
        )
        invisible_subtask = task.child_ids

        self.assertFalse(invisible_subtask.display_in_project)

        with Form(
            invisible_subtask,
            view="project.project_task_convert_to_subtask_view_form",
        ) as subtask_form:
            subtask_form.parent_id = self.env["project.task"]

        self.assertTrue(invisible_subtask.display_in_project)

    def test_convert_tasks_to_subtask(self) -> None:
        with Form(
            self.task_1,
            view="project.project_task_convert_to_subtask_view_form",
        ) as subtask:
            subtask.parent_id = self.task_2
        self.assertTrue(
            self.task_2 in self.task_1.parent_id,
            "Task2 should have Task1 as its parent.",
        )
        self.assertTrue(
            self.task_1 in self.task_2.child_ids,
            "Task1 should have Task2 as its child.",
        )

    def test_action_convert_to_subtask_on_private_task(self) -> None:
        private_task = self.env["project.task"].create(
            {
                "name": "Private task",
                "project_id": False,
            }
        )

        private_task_notification = private_task.action_convert_to_subtask()
        self.assertDictEqual(
            private_task_notification,
            {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "danger",
                    "message": "Private tasks cannot be converted into sub-tasks. Please set a project on the task to gain access to this feature.",
                },
            },
        )

    def test_display_in_project_is_correctly_set_when_parent_task_changes(
        self,
    ) -> None:
        task = self.env["project.task"].create(
            {
                "name": "Parent task",
                "project_id": self.project_goats.id,
                "child_ids": [
                    Command.create(
                        {
                            "name": "Sub-task 1",
                            "project_id": self.project_goats.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Sub-task 1",
                            "project_id": self.project_pigs.id,
                        }
                    ),
                ],
            }
        )
        subtask_1 = task.child_ids.filtered(
            lambda c: c.project_id == self.project_goats
        )
        subtask_2 = task.child_ids.filtered(lambda c: c.project_id == self.project_pigs)

        self.assertFalse(subtask_1.display_in_project)
        self.assertTrue(subtask_2.display_in_project)

        form_view = self.env.ref("project.project_task_convert_to_subtask_view_form")
        with Form(subtask_1, view=form_view) as subtask_form:
            subtask_form.parent_id = self.env["project.task"]

        self.assertTrue(subtask_1.display_in_project)

        with Form(subtask_1, view=form_view) as subtask_form:
            subtask_form.parent_id = task

        self.assertFalse(subtask_1.display_in_project)

        with Form(subtask_2, view=form_view) as subtask_form:
            subtask_form.parent_id = self.env["project.task"]

        self.assertTrue(subtask_2.display_in_project)

        with Form(subtask_2, view=form_view) as subtask_form:
            subtask_form.parent_id = task

        self.assertTrue(subtask_2.display_in_project)

    def test_subtask_private_project_and_parent_task(self) -> None:
        private_project = self.env["project.project"].create(
            {
                "name": "Private Project",
                "privacy_visibility": "followers",
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Parent Task",
                "project_id": private_project.id,
            }
        )
        employee = self.env["res.users"].create(
            {
                "name": "Employee",
                "login": "employee",
                "email": "employee@odoo.com",
                "group_ids": [(6, 0, [self.env.ref("project.group_project_user").id])],
            }
        )
        subtask = self.env["project.task"].create(
            {
                "name": "Subtask",
                "parent_id": task.id,
                "project_id": private_project.id,
                "user_ids": [(4, employee.id)],
            }
        )

        parent_dependent_fields = [
            name
            for name, field in self.env["project.task"]._fields.items()
            if field.compute
            and any(
                dep.startswith("parent_id")
                for dep in field.get_depends(self.env["project.task"])[0]
            )
        ]

        self.env.invalidate_all()
        subtask_data = subtask.with_user(employee).read(parent_dependent_fields)
        self.assertTrue(
            subtask_data,
            "The employee should be able to read the subtask data.",
        )

    def test_subtasks_inherits_tags_of_parent(self) -> None:
        task = self.env["project.task"].create(
            {
                "name": "Parent task",
                "project_id": self.project_goats.id,
                "tag_ids": [
                    Command.create({"name": "tag1", "color": 0}),
                    Command.create({"name": "tag2", "color": 1}),
                ],
            }
        )

        subtask1 = (
            self.env["project.task"]
            .with_context({"default_parent_id": task.id})
            .create(
                {
                    "name": "Sub-task 1",
                    "project_id": self.project_goats.id,
                }
            )
        )

        self.assertEqual(
            subtask1.tag_ids,
            task.tag_ids,
            "Subtask should inherit tags from parent task",
        )

    def test_subtask_default_tags_are_commands(self) -> None:
        task = self.env["project.task"].create(
            {
                "name": "Parent task",
                "project_id": self.project_goats.id,
                "tag_ids": [
                    Command.create({"name": "tag1", "color": 0}),
                    Command.create({"name": "tag2", "color": 1}),
                ],
            }
        )

        defaults = (
            self.env["project.task"]
            .with_context({"default_parent_id": task.id})
            .default_get(["tag_ids"])
        )

        self.assertEqual(defaults["tag_ids"], [Command.set(task.tag_ids.ids)])
        for command in defaults["tag_ids"]:
            self.assertIsInstance(
                command[0],
                int,
                "each command must start with an int code, so that "
                "`command[0] == Command.SET` is a valid comparison",
            )
