from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestTaskAnalysis(TestCommonTimesheet):

    def test_remaining_hours_includes_subtasks(self):
        self.task1.allocated_hours = 2.0
        subtask = self.env['project.task'].create({
            'name': 'Subtask One',
            'project_id': self.project_customer.id,
            'parent_id': self.task1.id,
        })
        self.env['account.analytic.line'].create({
            'name': 'Timesheet on subtask',
            'project_id': self.project_customer.id,
            'task_id': subtask.id,
            'unit_amount': 2.0,
            'employee_id': self.empl_employee.id,
        })

        self.env.flush_all()

        task_report = self.env['report.project.task.user'].search([('task_id', '=', self.task1.id)])
        self.assertEqual(len(task_report), 1, "The task should have exactly one row in the task analysis report")
        self.assertEqual(self.task1.remaining_hours, 0.0)
        self.assertEqual(
            task_report.remaining_hours, self.task1.remaining_hours,
            "The time remaining in the task analysis report should subtract the time spent on the sub-tasks, as the task does",
        )
