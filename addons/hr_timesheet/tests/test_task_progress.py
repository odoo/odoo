from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestTaskProgress(TestCommonTimesheet):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.task1.allocated_hours = 1.0
        cls.env['account.analytic.line'].create({
            'name': 'Timesheet on the small task',
            'project_id': cls.project_customer.id,
            'task_id': cls.task1.id,
            'unit_amount': 1.0,
            'employee_id': cls.empl_employee.id,
        })
        cls.task2.allocated_hours = 99.0

    def _get_average_progress(self):
        self.env.flush_all()
        [(progress,)] = self.env['project.task']._read_group(
            [('project_id', '=', self.project_customer.id)],
            aggregates=['progress:avg'],
        )
        return round(progress, 2)

    def test_progress_average_is_weighted_by_allocated_hours(self):
        self.assertEqual(
            self._get_average_progress(), 0.01,
            "1 hour spent out of the 100 allocated ones is 1% done, not the 50% average of both tasks' progress",
        )

    def test_progress_average_ignores_tasks_without_allocated_hours(self):
        self.env['account.analytic.line'].create({
            'name': 'Timesheet on a task with no allocated time',
            'project_id': self.project_customer.id,
            'task_id': self.env['project.task'].create({
                'name': 'Task Without Allocated Time',
                'project_id': self.project_customer.id,
            }).id,
            'unit_amount': 5.0,
            'employee_id': self.empl_employee.id,
        })
        self.assertEqual(
            self._get_average_progress(), 0.01,
            "A task without allocated time has no progress and should not weigh on the average",
        )
