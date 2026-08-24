from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestSaleTimesheetReport(TestCommonSaleTimesheet):

    _test_user_groups = None  # FIXME list needed groups

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

    def test_timesheet_report_fixed_price_rounding(self):
        '''Test timesheet revenue for a fixed-price service sold in days:
        2 days @ 800/day with 10% discount, 1 hour timesheeted -> revenue must be 720 * 1/8 = 90.
        '''
        uom_days = self.env.ref('uom.product_uom_day')
        self.product_order_timesheet3.write({'uom_id': uom_days})

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
        })
        so_line = self.env['sale.order.line'].create({
            'product_id': self.product_order_timesheet3.id,
            'product_uom_qty': 2,
            'order_id': sale_order.id,
            'price_unit': 800.0,
            'discount': 10.0,
        })
        sale_order.action_confirm()
        task = self.env['project.task'].search([('sale_line_id', '=', so_line.id)])

        ts = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 1,
            'employee_id': self.employee_user.id,
            'so_line': so_line.id,
            'order_id': sale_order.id,
        })
        self.env.flush_all()
        report = self.env['timesheets.analysis.report'].browse(ts.id)
        self.assertEqual(report.timesheet_revenues, 90.0)

    def _log_timesheet_on_sol(self, so_line, unit_amount, employee):
        """Confirm the SO of `so_line` and timesheet `unit_amount` on the task it generated."""
        so_line.order_id.action_confirm()
        task = so_line.task_id
        self.assertTrue(task, "The service should have generated a task to timesheet on")
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': unit_amount,
            'employee_id': employee.id,
        })
        self.env.flush_all()
        return timesheet, self.env['timesheets.analysis.report'].browse(timesheet.id)

    def test_timesheet_report_measures_time_and_material(self):
        """Time & Material service (delivered, timesheet): the revenue is the time spent
           multiplied by the price per hour of the sales order item, and the margin is
           that revenue minus the cost of the timesheet.
        """
        so_line = self.env['sale.order.line'].create({
            'product_id': self.product_delivery_timesheet2.id,
            'product_uom_qty': 5,
            'price_unit': 100.0,
            'order_id': self.env['sale.order'].create({'partner_id': self.partner_a.id}).id,
        })
        timesheet, report = self._log_timesheet_on_sol(so_line, 3, self.employee_user)

        self.assertEqual(report.billable_type, '04_billable_time')
        self.assertEqual(report.timesheet_revenues, 300.0, "3h at 100/hour")
        self.assertEqual(report.billable_time, 3.0)
        self.assertEqual(report.non_billable_time, 0.0)
        self.assertEqual(timesheet.amount, -45.0, "3h at a cost of 15/hour")
        self.assertEqual(report.margin, 255.0, "300 of revenues minus 45 of costs")

    def test_timesheet_report_measures_prepaid_service(self):
        """Prepaid/fixed price service (ordered): the revenue per unit comes from the
           untaxed total of the sales order item, so the discount is taken into account.
        """
        so_line = self.env['sale.order.line'].create({
            'product_id': self.product_order_timesheet2.id,
            'product_uom_qty': 4,
            'price_unit': 100.0,
            'discount': 10.0,
            'order_id': self.env['sale.order'].create({'partner_id': self.partner_a.id}).id,
        })
        timesheet, report = self._log_timesheet_on_sol(so_line, 2, self.employee_user)

        self.assertEqual(so_line.price_subtotal, 360.0)
        self.assertEqual(report.billable_type, '02_billable_fixed')
        self.assertEqual(report.timesheet_revenues, 180.0, "2h at 360/4 = 90 per hour")
        self.assertEqual(report.billable_time, 2.0)
        self.assertEqual(report.non_billable_time, 0.0)
        self.assertEqual(timesheet.amount, -30.0)
        self.assertEqual(report.margin, 150.0)

    def test_timesheet_report_measures_manual_service(self):
        """A manual service is not invoiced from the timesheets, so it generates no
           timesheet revenue, but the time spent stays billable.
        """
        so_line = self.env['sale.order.line'].create({
            'product_id': self.product_delivery_manual2.id,
            'product_uom_qty': 5,
            'price_unit': 100.0,
            'order_id': self.env['sale.order'].create({'partner_id': self.partner_a.id}).id,
        })
        timesheet, report = self._log_timesheet_on_sol(so_line, 3, self.employee_user)

        self.assertEqual(report.billable_type, '08_billable_manual')
        self.assertEqual(report.timesheet_revenues, 0.0, "A manual service generates no timesheet revenue")
        self.assertEqual(report.billable_time, 3.0, "The time spent is still linked to a sales order item")
        self.assertEqual(report.non_billable_time, 0.0)
        self.assertEqual(report.margin, timesheet.amount, "Without revenues the margin is the cost of the timesheet")

    def test_timesheet_report_measures_milestone_service(self):
        """A milestone service is not invoiced from the timesheets either, so it
           generates no timesheet revenue.
        """
        product_milestone = self.env['product.product'].create({
            'name': "Service milestones, create task in global project",
            'type': 'service',
            'invoice_policy': 'delivery',
            'service_type': 'milestones',
            'service_tracking': 'task_global_project',
            'project_id': self.project_global.id,
            'uom_id': self.uom_hour.id,
            'list_price': 100.0,
            'taxes_id': False,
        })
        so_line = self.env['sale.order.line'].create({
            'product_id': product_milestone.id,
            'product_uom_qty': 5,
            'order_id': self.env['sale.order'].create({'partner_id': self.partner_a.id}).id,
        })
        timesheet, report = self._log_timesheet_on_sol(so_line, 2, self.employee_user)

        self.assertEqual(report.billable_type, '06_billable_milestones')
        self.assertEqual(report.timesheet_revenues, 0.0, "A milestone service generates no timesheet revenue")
        self.assertEqual(report.billable_time, 2.0)
        self.assertEqual(report.non_billable_time, 0.0)
        self.assertEqual(report.margin, timesheet.amount)

    def test_timesheet_report_measures_non_billable(self):
        """A timesheet without sales order item is non-billable: no revenue, and the
           whole time spent is reported as non-billable.
        """
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': self.project_non_billable.id,
            'unit_amount': 4,
            'employee_id': self.employee_manager.id,
        })
        self.env.flush_all()
        report = self.env['timesheets.analysis.report'].browse(timesheet.id)

        self.assertEqual(report.billable_type, '09_non_billable')
        self.assertEqual(report.timesheet_revenues, 0.0)
        self.assertEqual(report.billable_time, 0.0)
        self.assertEqual(report.non_billable_time, 4.0)
        self.assertEqual(timesheet.amount, -180.0, "4h at a cost of 45/hour")
        self.assertEqual(report.margin, -180.0, "Without revenues the margin is the cost of the timesheet")
