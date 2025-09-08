from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestTaskTemplates(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_with_templates = cls.env["project.project"].create({
            "name": "Project with Task Template",
        })
        cls.template_task = cls.env["project.task"].create({
            "name": "Template",
            "project_id": cls.project_with_templates.id,
            "is_template": True,
            "description": "Template description",
            "partner_id": cls.partner_1.id,
        })
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
