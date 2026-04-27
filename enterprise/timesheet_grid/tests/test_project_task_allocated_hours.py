# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.project_enterprise.tests.test_task_gantt_view import TestTaskGanttView


@tagged('-at_install', 'post_install')
class TestTaskAllocatedHours(TestTaskGanttView):

    def test_capacity_split_allocated_hours_substitute(self):
        self.tasks |= self.env['project.task'].create({
            'name': 'Test gantt',
            'project_id': self.project_gantt_test_1.id,
            'allocated_hours': 12.0,
        })
        self.tasks.write({
            'user_ids': [self.project_gantt_test_1.user_id.id],
            'planned_date_begin': '2024-03-07 00:00:00',
            'date_deadline': '2024-03-08 23:59:59',
        })  # capacity of 16h
        self.assertEqual(self.tasks.mapped('allocated_hours'), [2.0, 2.0, 12.0], 'The capacity should be 4h since a task with 12h allocated hours is in the recordset')
