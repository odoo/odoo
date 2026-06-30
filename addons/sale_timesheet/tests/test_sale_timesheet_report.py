from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestSaleTimesheetReport(TestCommonSaleTimesheet):

    def test_timesheet_report_uom_difference(self):
        '''Test the timesheet revenue are correctly computed in case of a
           fixed price service
        '''
        uom_days = self.env.ref('uom.product_uom_day')

        # Change product uom from hours to days
        self.product_order_timesheet3.write({
            'uom_id': uom_days,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
        })
        so_line = self.env['sale.order.line'].create({
            'product_id': self.product_order_timesheet3.id,
            'product_uom_qty': 3,
            'order_id': sale_order.id,
            'price_unit': 10.0,
            'tax_ids': [Command.set(self.tax_sale_a.ids)],
        })
        sale_order.action_confirm()
        task = self.env['project.task'].search([('sale_line_id', '=', so_line.id)])

        # Register a timesheet entry of 24 hours
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 24,
            'employee_id': self.employee_user.id,
            'so_line': so_line.id,
            'order_id': sale_order.id,
        })
        self.env.flush_all()

        report = self.env['timesheets.analysis.report'].search([('so_line', '=', so_line.id)])
        self.assertEqual(report.unit_amount, 24)
        self.assertEqual(report.timesheet_revenues, 30)
        self.assertEqual(report.billable_time, 24)
