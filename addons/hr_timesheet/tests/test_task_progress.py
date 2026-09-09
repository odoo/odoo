from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestTaskProgress(TestCommonTimesheet):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # One hour allocated and spent, against 99 hours allocated and
        # untouched: the group is 1% done, while the average of both
        # progresses is 50%.
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
            self._get_average_progress(), 1.0,
            "The average progress should weigh each task by its allocated time, not count every task equally",
        )
