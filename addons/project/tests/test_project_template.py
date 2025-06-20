from odoo.exceptions import UserError
from odoo import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestProjectTemplates(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_template = cls.env["project.project"].create({
            "name": "Project Template",
            "is_template": True,
        })
        cls.task_inside_template = cls.env["project.task"].create({
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

        self.assertEqual(len(project.task_ids), 1, "The tasks of the template should be copied too.")

    def test_copy_template(self):
        """
        A copy of a template should be a template
        """
        copied_template = self.project_template.copy()
        self.assertEqual(copied_template.name, "Project Template (copy)", "The project name should be `Project Template` (copy).")
        self.assertTrue(copied_template.is_template, "The copy of the template should also be a template.")
        self.assertEqual(len(copied_template.task_ids), 1, "The child of the template should be copied too.")

    def test_revert_template(self):
        """
        A revert of a template should not be a template
        """
        self.project_template.action_undo_convert_to_template()
        self.assertFalse(self.project_template.is_template, "The reverted template should become a normal template.")

    def test_revert_task_template(self):
        """
        A template task should not be reverted to a regular task.
        """
        self.task_inside_template.is_template = True
        with self.assertRaises(UserError, msg="A UserError should be raised when attempting to revert a template task to a regular one."):
            self.task_inside_template.action_convert_to_template()

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
            'task_ids': [
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
