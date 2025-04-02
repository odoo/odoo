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
            "active": False,
            "is_template": True,
            "description": "Template description",
        })
        cls.child_task = cls.env["project.task"].create({
            "name": "Child Task",
            "parent_id": cls.template_task.id,
            "active": False,
            "description": "Child description",
        })

    def test_create_from_template(self):
        """
        Creating a task through the action should result in an active, non template copy
        """
        task_id = self.template_task.action_create_from_template()
        task = self.env["project.task"].browse(task_id)
        self.assertFalse(task.is_template, "The created task should be a normal task and not a template.")
        self.assertTrue(task.active, "The created task should not be archived.")

        self.assertEqual(len(task.with_context(active_test=False).child_ids), 1, "The child of the template should be copied too.")
        child_task = task.with_context(active_test=False).child_ids
        self.assertTrue(child_task.active, "The child task should be active too.")
        self.assertFalse(child_task.is_template, "The child task should still not be a template.")

    def test_copy_archived_template(self):
        """
        Copying a template should preserve its archived status
        """
        copied_template = self.template_task.copy()
        self.assertFalse(copied_template.active, "The copied template should also be archived.")

        self.assertEqual(len(copied_template.with_context(active_test=False).child_ids), 1, "The child of the template should be copied too.")
        copied_template_child_task = copied_template.with_context(active_test=False).child_ids
        self.assertFalse(copied_template_child_task.active, "The child task should be archived.")
        self.assertFalse(copied_template_child_task.is_template, "The child task should still not be a template.")

    def test_copy_project_with_templates(self):
        """
        Copying a project should also copy its task templates
        """
        copied_project = self.project_with_templates.copy()
        task = self.env["project.task"].with_context(active_test=False).search([("project_id", "=", copied_project.id)], order="id asc", limit=1)
        self.assertTrue(task, "The copied project should contain a copy of the template.")
        self.assertTrue(task.is_template, "The copied template should still be a template.")
        self.assertFalse(task.active, "The copied template should still be archived")
