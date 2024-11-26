# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.test_sale_timesheet import TestSaleTimesheet
from odoo.tests import tagged
from odoo.fields import Command


@tagged('post_install', '-at_install')
class TestPerformanceTimesheet(TestSaleTimesheet):

    def test_performance_billable_project_change_customer(self):
        """
            Use case: change the partner of a billable project containing many tasks having no SOL, which should trigger _compute_sale_line_id() of all tasks.
            We check if the number of queries does not increase proportionally to the number of tasks.
        """
        project = self.env['project.project'].create({
            'name': 'Perf Project',
            'task_ids': [Command.create({'name': f'Task {i}'}) for i in range(50)]
        })
        self.assertFalse(project.task_ids.sale_line_id)
        self.env.invalidate_all()
        with self.assertQueryCount(83):
            project.write({
                'allow_billable': True,
                'partner_id': self.partner_b.id,
            })
        self.assertTrue(project.task_ids.sale_line_id)

        # Reset all tasks's SOL to False, double the number of tasks and run it again
        project.allow_billable = False
        self.assertFalse(project.task_ids.sale_line_id)
        self.env['project.task'].create([{
            'name': f'Task {i}',
            'project_id': project.id,
        } for i in range(50, 100)])
        self.env.invalidate_all()
        with self.assertQueryCount(130):
            project.write({
                'allow_billable': True,
                'partner_id': self.partner_b.id,
            })
        self.assertTrue(project.task_ids.sale_line_id)
