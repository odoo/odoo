from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestTaskTemplates(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_with_templates = cls.env["project.project"].create({
            "name": "Project with Task Template",
        })
        cls.template_task = cls.env["project.task.template"].create({
            "name": "Template",
            "project_id": cls.project_with_templates.id,
            "description": "Template description",
        })
        cls.child_task = cls.env["project.task.template"].create({
            "name": "Child Task",
            "parent_id": cls.template_task.id,
            "description": "Child description",
        })

    def test_create_from_template(self):
        """
        Creating a task through the action should result in a non template copy, with no partner_id
        """
        task_id = self.template_task.action_create_from_template()
        task = self.env["project.task"].browse(task_id)
        self.assertFalse(task.partner_id, "The created task should not have a partner.")

        self.assertEqual(len(task.child_ids), 1, "The child of the template should be copied too.")
        child_task = task.child_ids
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
        self.assertEqual(len(copied_template.child_ids), 1, "The child of the template should be copied too.")

    def test_copy_project_with_templates(self):
        """
        Copying a project should also copy its task templates
        """
        self.project_with_templates.is_template = True
        copied_project = self.project_with_templates.copy()
        task_template = self.env["project.task.template"].search([("project_id", "=", copied_project.id)], order="id asc", limit=1)
        self.assertTrue(task_template, "The copied project should contain a copy of the template.")
