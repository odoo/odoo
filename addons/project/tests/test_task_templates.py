from odoo import Command
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import tagged


@tagged('at_install', '-post_install')  # LEGACY at_install, fails post install
class TestTaskTemplates(TestProjectCommon, MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_with_templates = cls.env["project.project"].create({
            "name": "Project with Task Template",
        })
        cls.template_task, cls.template_task_without_project = cls.env["project.task"].create([
            {
                "name": "Template",
                "project_id": cls.project_with_templates.id,
                "is_template": True,
                "description": "Template description",
                "partner_id": cls.partner_1.id,
            },
            {
                "name": "Template without project",
                "is_template": True,
                "project_id": False,
            }
        ])
        cls.child_task = cls.env["project.task"].create({
            "name": "Child Task",
            "parent_id": cls.template_task.id,
            "description": "Child description",
            "partner_id": cls.partner_2.id,
        })

    def test_create_from_template(self):
        """
        Creating a task through the action should result in a non template copy, with no partner_id
        """
        task_id = self.template_task.action_create_from_template()
        task = self.env["project.task"].browse(task_id)
        self.assertFalse(task.is_template, "The created task should be a normal task and not a template.")
        self.assertFalse(task.partner_id, "The created task should not have a partner.")

        self.assertEqual(len(task.child_ids), 1, "The child of the template should be copied too.")
        child_task = task.child_ids
        self.assertFalse(child_task.is_template, "The child task should still not be a template.")
        self.assertFalse(child_task.partner_id, "The child task should also not have a partner.")

        # With a partner set on the project, new tasks should get the partner too, even if created from a template
        self.project_with_templates.partner_id = self.partner_3

        task_id = self.template_task.action_create_from_template()
        task = self.env["project.task"].browse(task_id)
        self.assertEqual(task.partner_id, self.partner_3, "The created task should have the same partner as the project.")
        child_task = task.child_ids
        self.assertEqual(child_task.partner_id, self.partner_3, "The child of the created task should have the same partner as the project.")

    def test_copy_template(self):
        """
        A copy of a template should be a template
        """
        copied_template = self.template_task.copy()
        self.assertTrue(copied_template.is_template, "The copy of the template should also be a template.")
        self.assertEqual(len(copied_template.child_ids), 1, "The child of the template should be copied too.")
        copied_template_child_task = copied_template.child_ids
        self.assertFalse(copied_template_child_task.is_template, "The child of the copy should still not be a template.")

    def test_copy_project_with_templates(self):
        """
        Copying a project should also copy its task templates
        """
        copied_project = self.project_with_templates.copy()
        task = self.env["project.task"].search([("project_id", "=", copied_project.id)], order="id asc", limit=1)
        self.assertTrue(task, "The copied project should contain a copy of the template.")
        self.assertTrue(task.is_template, "The copied template should still be a template.")

    def test_has_template_ancestor(self):
        self.assertTrue(self.template_task.has_template_ancestor, "The template is a template.")
        self.assertTrue(self.child_task.has_template_ancestor, "The child of the template has a template ancestor.")

        task = self.env["project.task"].create({
            "name": "Task",
            "project_id": self.project_with_templates.id,
        })
        self.assertFalse(task.has_template_ancestor, "The task does not have ancestors and is not a template.")

        child = self.env["project.task"].create({
            "name": "Child",
            "parent_id": task.id,
        })
        self.assertFalse(child.has_template_ancestor, "The task has ancestors, but none of them are templates.")

        self.assertCountEqual(
            self.env["project.task"].search(
                [('project_id', '=', self.project_with_templates.id), ('has_template_ancestor', '=', True)],
            ),
            self.template_task | self.child_task,
            "The search should find the template and its child",
        )
        self.assertCountEqual(
            self.env["project.task"].search(
                [('project_id', '=', self.project_with_templates.id), ('has_template_ancestor', '=', False)],
            ),
            task | child,
            "The search should find the non template task and its child",
        )

    def test_send_creation_email_on_task_creation_from_template(self):
        self.template_task.project_id.message_subscribe(
            partner_ids=self.user_projectuser.partner_id.ids,
            subtype_ids=(self.env.ref('mail.mt_comment') + self.env.ref('project.mt_task_new')).ids
        )
        with self.mock_mail_gateway():
            task_id = self.template_task.with_user(self.user_projectmanager).action_create_from_template()
        task = self.env["project.task"].browse(task_id)
        self.assertEqual(task.message_ids[0].subtype_id, self.env.ref('project.mt_task_new'))
        self.assertEqual(task.message_ids[0].notified_partner_ids, self.user_projectuser.partner_id)

    def test_task_template_without_project_creation(self):
        """
        Creating a task template without a project should be possible and it can have child tasks as well as a parent task.
        It should also allow recurring tasks and task dependencies, and have no stage by default.
        """
        regular_task_1, regular_task_2 = self.env["project.task"].create([
            {
                "name": "Regular task 1",
                "project_id": self.project_with_templates.id,
            },
            {
                "name": "Regular task 2",
                "project_id": self.project_with_templates.id,
            }
        ])
        self.template_task_without_project.child_ids = self.template_task + regular_task_1
        self.template_task_without_project.parent_id = regular_task_2
        self.assertFalse(self.template_task_without_project.project_id, "The created task template without project should not have a project.")
        self.assertTrue(self.template_task_without_project.is_template, "The created task template without project should be a template.")
        self.assertEqual(self.template_task_without_project.child_ids, self.template_task + regular_task_1, "The task template without project should have two child tasks.")
        self.assertEqual(self.template_task_without_project.parent_id, regular_task_2, "The task template without project should have a parent task.")
        self.assertTrue(self.template_task_without_project.allow_task_dependencies, "The task template without project should allow task dependencies by default.")
        self.assertTrue(self.template_task_without_project.allow_recurring_tasks, "The task template without project should allow recurring tasks by default.")
        self.assertFalse(self.template_task_without_project.stage_id, "The task template without project should not have a stage by default.")

    def test_create_task_from_template_without_project(self):
        """
        Creating a task from a template without a project.
        It should only copy the recurrence if the project has recurrence enabled, as well as the task dependencies if the project has them enabled.
        """
        self.template_task_without_project.write({
            "recurring_task": True,
            "repeat_type": "forever",
            "repeat_unit": "month",
            "repeat_interval": 3,
            "depend_on_ids": [Command.set(self.template_task.ids)],
        })
        self.project_with_templates.write({
            "allow_recurring_tasks": False,
            "allow_task_dependencies": False,
        })
        task_1_id = self.template_task_without_project.with_context(default_project_id=self.project_with_templates.id).action_create_from_template()
        task_1 = self.env["project.task"].browse(task_1_id)
        self.assertEqual(task_1.project_id, self.project_with_templates, "The created task should be in the project that was set in the context.")
        self.assertFalse(task_1.is_template, "The created task should be a normal task and not a template.")
        self.assertFalse(task_1.recurring_task, "The created task should not be recurring as the project has recurring tasks disabled.")
        self.assertFalse(task_1.recurrence_id, "The created task should not have a recurrence as the project has recurring tasks disabled.")
        self.assertFalse(task_1.depend_on_ids, "The created task should not have dependencies as the project has task dependencies disabled.")

        self.project_with_templates.write({
            "allow_recurring_tasks": True,
            "allow_task_dependencies": True,
        })
        task_2_id = self.template_task_without_project.with_context(default_project_id=self.project_with_templates.id).action_create_from_template()
        task_2 = self.env["project.task"].browse(task_2_id)
        self.assertEqual(task_2.project_id, self.project_with_templates, "The created task should be in the project that was set in the context.")
        self.assertTrue(task_2.recurring_task, "The created task should be recurring as the project has recurring tasks enabled.")
        self.assertTrue(task_2.recurrence_id, "The created task should have a recurrence as the project has recurring tasks enabled.")
        self.assertEqual(task_2.repeat_type, "forever", "The created task should have the same repeat type as the template as the project has recurring tasks enabled.")
        self.assertEqual(task_2.repeat_unit, "month", "The created task should have the same repeat unit as the template as the project has recurring tasks enabled.")
        self.assertEqual(task_2.repeat_interval, 3, "The created task should have the same repeat interval as the template as the project has recurring tasks enabled.")
        self.assertEqual(task_2.depend_on_ids, self.template_task, "The created task should have the same dependencies as the template as the project has task dependencies enabled.")
