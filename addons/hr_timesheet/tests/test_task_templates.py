from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTaskTemplates(TransactionCase):

    def test_create_task_from_template_without_project_in_timesheetable_project(self):
        """
        Creating a task from a template without a project.
        It should only enable timesheets if the project has timesheets enabled, as well as copying the allocated hours.
        """
        project = self.env["project.project"].create({
            "name": "Test Project",
        })
        template_task_without_project = self.env["project.task"].create({
            "name": "Task Template without Project",
            "project_id": False,
            "is_template": True,
            "allocated_hours": 5.0,
        })

        project.allow_timesheets = False
        self.assertTrue(template_task_without_project.allow_timesheets, "The template task should have timesheets enabled as it is a template without project.")
        task_1_id = template_task_without_project.with_context(default_project_id=project.id).action_create_from_template()
        task_1 = self.env["project.task"].browse(task_1_id)
        self.assertFalse(task_1.allow_timesheets, "The created task should not have timesheets enabled as the project has timesheets disabled.")
        self.assertEqual(task_1.allocated_hours, 0.0, "The created task should not have allocated hours as the project has timesheets disabled.")

        project.allow_timesheets = True
        task_2_id = template_task_without_project.with_context(default_project_id=project.id).action_create_from_template()
        task_2 = self.env["project.task"].browse(task_2_id)
        self.assertTrue(task_2.allow_timesheets, "The created task should have timesheets enabled as the project has timesheets enabled.")
        self.assertEqual(task_2.allocated_hours, 5.0, "The created task should have the same allocated hours as the template as the project has timesheets enabled.")
