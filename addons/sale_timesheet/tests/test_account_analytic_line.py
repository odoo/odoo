from odoo.tests import tagged

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestAccountAnalyticLine(TestCommonSaleTimesheet):

    _test_user_groups = None  # FIXME list needed groups

    def test_timesheet_product_from_sale_line(self):
        sale_line = self.so.order_line.filtered(lambda sol: sol.product_id == self.product_delivery_timesheet2)
        task = self.env['project.task'].search([('sale_line_id', '=', sale_line.id)])
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Timesheet',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 3,
            'employee_id': self.employee_user.id,
        })

        self.assertEqual(timesheet.so_line, sale_line)
        self.assertEqual(
            timesheet.product_id, self.product_delivery_timesheet2,
            "The product of the timesheet should be the one of its sales order item.")
        self.assertEqual(
            timesheet.product_uom_id, self.env.company.project_time_mode_id,
            "The timesheet should still be encoded in the time unit of the company.")

        other_sale_line = self.so.order_line.filtered(lambda sol: sol.product_id == self.product_delivery_timesheet1)
        timesheet.so_line = other_sale_line
        self.assertEqual(
            timesheet.product_id, self.product_delivery_timesheet1,
            "The product of the timesheet should follow its sales order item.")

    def test_timesheet_product_without_sale_line(self):
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Timesheet',
            'project_id': self.project_non_billable.id,
            'unit_amount': 3,
            'employee_id': self.employee_user.id,
        })

        self.assertFalse(timesheet.so_line)
        self.assertFalse(
            timesheet.product_id,
            "A non-billable timesheet should have no product.")
