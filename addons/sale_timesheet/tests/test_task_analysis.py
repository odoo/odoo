from odoo.tests import tagged

from .common import TestCommonSaleTimesheet


@tagged('post_install', '-at_install')
class TestSaleTimesheetTaskAnalysis(TestCommonSaleTimesheet):
    def test_remaining_hours_so(self):
        sales_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        so_line_1 = self.env['sale.order.line'].create({
            'product_id': self.product_order_timesheet3.id,
            'product_uom_qty': 10,
            'order_id': sales_order.id,
        })
        sales_order.action_confirm()

        task_1 = self.env['project.task'].search([('sale_line_id', '=', so_line_1.id)])
        task_2 = self.env['project.task'].create({
            'name': "Task 2",
            'project_id': task_1.project_id.id,
            'partner_id': self.partner_a.id,
            'sale_line_id': so_line_1.id,
        })
        self.assertEqual(task_2.remaining_hours_so, 10)

        self.env.flush_all()
        task_report = self.env['report.project.task.user'].search([('task_id', '=', task_2.id)])
        self.assertEqual(task_report.remaining_hours_so, task_2.remaining_hours_so)
