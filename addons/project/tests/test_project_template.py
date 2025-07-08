from datetime import date

from odoo import Command
from odoo.tests import freeze_time

from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestProjectTemplates(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_template = cls.env["project.project"].create({
            "name": "Project Template",
            "is_template": True,
            "date_start": date(2025, 6, 1),
            "date": date(2025, 6, 11),
        })
        cls.task_inside_template = cls.env["project.task.template"].create({
            "name": "Task in Project Template",
            "project_id": cls.project_template.id,
        })

    def test_create_from_template(self):
        """
        Creating a project through the action should result in a non template copy
        """
        project = self.project_template.action_create_from_template()
        self.assertEqual(project.name, "Project Template", "The project name should be `Project Template`.")
        self.assertFalse(project.is_template, "The created Project should be a normal project and not a template.")
        self.assertFalse(project.partner_id, "The created Project should not have a customer.")

        template_task_count = self.env['project.task.template'].search_count([('project_id', '=', project.id)])
        self.assertEqual(template_task_count, 0, "The tasks of the template should be copied too.")

    def test_copy_template(self):
        """
        A copy of a template should be a template
        """
        copied_template = self.project_template.copy()
        self.assertEqual(copied_template.name, "Project Template (copy)", "The project name should be `Project Template` (copy).")
        self.assertTrue(copied_template.is_template, "The copy of the template should also be a template.")
        task_count = self.env['project.task.template'].search_count([('project_id', '=', copied_template.id)])
        self.assertEqual(task_count, 1, "The child of the template should be copied too.")

    def test_revert_template(self):
        """
        A revert of a template should not be a template
        """
        self.project_template.action_undo_convert_to_template()
        self.assertFalse(self.project_template.is_template, "The reverted template should become a normal template.")

    def test_tasks_dispatching_from_template(self):
        """
        The tasks of a project template should be dispatched to the new project according to the role-to-users mapping defined
        on the project template wizard.
        """
        role1, role2, role3, role4, role5 = self.env['project.role'].create([
            {'name': 'Developer'},
            {'name': 'Designer'},
            {'name': 'Project Manager'},
            {'name': 'Tester'},
            {'name': 'Product Owner'},
        ])
        project_template = self.env['project.project'].create({
            'name': 'Project template',
            'is_template': True,
            'task_template_ids': [
                Command.create({
                    'name': 'Task 1',
                    'role_ids': [role1.id, role3.id],
                }),
                Command.create({
                    'name': 'Task 2',
                    'role_ids': [role5.id, role4.id],
                }),
                Command.create({
                    'name': 'Task 3',
                    'role_ids': [role2.id, role5.id],
                }),
                Command.create({
                    'name': 'Task 4',
                    'role_ids': [role3.id],
                }),
                Command.create({
                    'name': 'Task 5',
                    'role_ids': [role5.id],
                }),
                Command.create({
                    'name': 'Task 6',
                }),
                Command.create({
                    'name': 'Task 7',
                    'role_ids': [role2.id, role3.id],
                    'user_ids': [self.user_projectuser.id, self.user_projectmanager.id],
                }),
            ],
        })
        user1, user2 = self.env['res.users'].create([
            {
                'name': 'Test User 1',
                'login': 'test1',
                'password': 'testuser1',
                'email': 'test1.test@example.com',
            },
            {
                'name': 'Test User 2',
                'login': 'test2',
                'password': 'testuser2',
                'email': 'test2.test@example.com',
            }
        ])
        wizard = self.env['project.template.create.wizard'].create({
            'template_id': project_template.id,
            'name': 'New Project from Template',
            'role_to_users_ids': [
                Command.create({
                    'role_id': role1.id,
                    'user_ids': [self.user_projectuser.id, self.user_projectmanager.id],
                }),
                Command.create({
                    'role_id': role2.id,
                    'user_ids': [user1.id],
                }),
                Command.create({
                    'role_id': role3.id,
                    'user_ids': [user2.id],
                }),
                Command.create({
                    'role_id': role4.id,
                    'user_ids': [self.user_projectuser.id],
                }),
            ],
        })
        new_project = wizard._create_project_from_template()

        self.assertEqual(
            new_project.task_ids.filtered(lambda t: t.name == 'Task 1').user_ids,
            self.user_projectuser + self.user_projectmanager + user2,
            'Task 1 should be assigned to the users mapped to `role1` and `role3`.',
        )
        self.assertEqual(
            new_project.task_ids.filtered(lambda t: t.name == 'Task 2').user_ids,
            self.user_projectuser,
            'Task 2 should be assigned to the users mapped to `role4`. As `role5` is not in the mapping.',
        )
        self.assertEqual(
            new_project.task_ids.filtered(lambda t: t.name == 'Task 3').user_ids,
            user1,
            'Task 3 should be assigned to the users mapped to `role2`. As `role5` is not in the mapping.',
        )
        self.assertEqual(
            new_project.task_ids.filtered(lambda t: t.name == 'Task 4').user_ids,
            user2,
            'Task 4 should be assigned to the users mapped to `role3`.'
        )
        self.assertFalse(
            new_project.task_ids.filtered(lambda t: t.name == 'Task 5').user_ids,
            'Task 5 should not be assigned to any user as `role5` is not in the mapping.',
        )
        self.assertFalse(
            new_project.task_ids.filtered(lambda t: t.name == 'Task 6').user_ids,
            'Task 6 should not be assigned to any user as it has no role.',
        )
        self.assertEqual(
            new_project.task_ids.filtered(lambda t: t.name == 'Task 7').user_ids,
            self.user_projectuser + self.user_projectmanager + user1 + user2,
            'Task 7 should be assigned to the users mapped to `role2` and `role3`, plus the users who were already assigned to the task.'
        )

    @freeze_time("2025-06-15")
    def test_create_from_template_no_dates(self):
        today = date.today()

        new_project = self.project_template.action_create_from_template({
            "name": "New Project",
            "is_template": False,
        })

        expected_delta = self.project_template.date - self.project_template.date_start
        self.assertEqual(new_project.date_start, today, "Start date should default to today")
        self.assertEqual(new_project.date, today + expected_delta, "End date should be start + template delta")

    def test_create_from_template_start_only(self):
        new_start = date(2025, 7, 1)

        new_project = self.project_template.action_create_from_template({
            "name": "New Project",
            "is_template": False,
            "date_start": new_start,
        })

        expected_delta = self.project_template.date - self.project_template.date_start
        self.assertEqual(new_project.date_start, new_start, "Start date should be the one provided")
        self.assertEqual(new_project.date, new_start + expected_delta, "End date should be start + template delta")

    def test_create_from_template_with_dates(self):
        new_start = date(2025, 7, 1)
        new_end = date(2025, 7, 15)

        new_project = self.project_template.action_create_from_template({
            "name": "New Project",
            "is_template": False,
            "date_start": new_start,
            "date": new_end,
        })

        self.assertEqual(new_project.date_start, new_start, "Start date should be the one provided")
        self.assertEqual(new_project.date, new_end, "End date should be the one provided")

    def test_project_template_convert_regular_project_with_sub_task_template(self):
        """
        Test converting a project template into a regular project and ensure that
        sub-task templates are also copied correctly

            Project Template A
               |
               └── Task Template A
                        |
                        └── Task Template B
                            |
                            ├── Task Template C
                            └── Task Template D
                                |
                                └── Task Template E
        """
        project_template = self.env["project.project"].create({
            "name": "Project Template",
            "is_template": True,
        })

        self.env["project.task.template"].create({
            "name": "Task Template A",
            "project_id": project_template.id,
            "child_ids": [
                Command.create({
                    "name": "Task Template B",
                    "child_ids": [
                        Command.create({
                            "name": "Task Template C"
                        }),
                        Command.create({
                            "name": "Task Template D",
                            "child_ids": [
                                Command.create({"name": "Task Template E"})
                            ]
                        }),
                    ]
                }),
            ],
        })
        project = project_template.action_create_from_template()
        expected_hierarchy = {
            "Task Template A": None,
            "Task Template B": "Task Template A",
            "Task Template C": "Task Template B",
            "Task Template D": "Task Template B",
            "Task Template E": "Task Template D",
        }
        self.assertEqual(project.task_count, len(expected_hierarchy), "Unexpected number of tasks created")

        for task in project.task_ids:
            expected_parent_name = expected_hierarchy[task.name]
            if expected_parent_name:
                self.assertEqual(
                    task.parent_id.name,
                    expected_parent_name,
                    f"Task '{task.name}' should have parent '{expected_parent_name}'",
                )
            else:
                self.assertFalse(
                    task.parent_id,
                    f"Task '{task.name}' should not have a parent",
                )
        project_template_data = project.action_create_template_from_project()
        project_id = project_template_data.get('params')['project_id']
        project_template = self.env['project.project'].browse(project_id)
        self.assertEqual(len(project_template.task_template_ids), len(expected_hierarchy), "Unexpected number of tasks created")

        for task_template in project_template.task_template_ids:
            expected_parent_name = expected_hierarchy[task_template.name]
            if expected_parent_name:
                self.assertEqual(
                    task_template.parent_id.name,
                    expected_parent_name,
                    f"Task Template '{task_template.name}' should have parent '{expected_parent_name}'",
                )
            else:
                self.assertFalse(
                    task_template.parent_id,
                    f"Task Template '{task_template.name}' should not have a parent",
                )

    def test_project_create_from_project_template_with_dependent_task(self):
        """
        Steps:
        1. Create a project template.
        2. Create a task template.
        4. Generate a project from the project template.
        5. Ensure the dependency is preserved in the new project.
        """
        project_template = self.env["project.project"].create({
            "name": "Project Template",
            "is_template": True,
        })

        self.env["project.task.template"].create({
            "name": "Task Template A",
            "project_id": project_template.id,
            "depend_on_ids": [Command.set(self.task_2.ids)],
        })

        project = project_template.action_create_from_template()
        new_task_a = project.task_ids.filtered(lambda t: t.name == "Task Template A")
        self.assertEqual(
            new_task_a.depend_on_ids.ids,
            self.task_2.ids,
            "Dependency mismatch: Task Template A should depend on Task 2 in the generated project."
        )

    def test_recurrence_project_template_convert_regular_project(self):
        """
        Test recurrence of project template when converting to regular project
        Steps:
            - Create a project template.
            - Create a task template with recurring.
            - Convert the project template into a regular project.
            - Verify tasks in the created project.
        """
        project_template_recurring = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            "name": 'Project Template Recurring',
            "is_template": True,
        })
        task_template_recurring = self.env['project.task.template'].create({
            'name': "Recurring Task template",
            'project_id': project_template_recurring.id,
            'recurring_task': True,
            'repeat_interval': 2,
            'repeat_unit': 'week',
            'repeat_type': 'forever',
        })
        project = project_template_recurring.action_create_from_template()
        recurring_task = project.task_ids

        self.assertEqual(task_template_recurring.name, recurring_task.name, "Task name mismatch")
        self.assertTrue(task_template_recurring.recurring_task, "Task should be recurring")
        self.assertEqual(task_template_recurring.repeat_unit, recurring_task.repeat_unit, "Task repeat unit mismatch")
        self.assertEqual(task_template_recurring.repeat_type, recurring_task.repeat_type, "Task repeat type mismatch")
        self.assertEqual(task_template_recurring.repeat_interval, recurring_task.repeat_interval, "Task repeat interval mismatch")
