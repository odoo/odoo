from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestTaskAnalysis(TestCommonTimesheet):

    def test_progress_includes_subtasks(self):
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
        self.assertEqual(self.task1.progress, 100.0)
        self.assertEqual(
            task_report.progress, self.task1.progress,
            "The progress in the task analysis report should account for the time spent on the sub-tasks, as the task does",
        )
