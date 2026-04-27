from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet
from odoo.tests import Form

class TestProjectTaskQuickCreate(TestCommonTimesheet):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_customer.write({'allow_timesheets': True})

    def test_create_task_and_add_assignees(self):
        task_form = Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_customer.id}), view="project.quick_create_task_form")
        task_form.display_name = 'hello'
        task_form.user_ids.set(self.user_employee)
        self.assertEqual(task_form.display_name, 'hello')
