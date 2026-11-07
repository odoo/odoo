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

    def test_timesheet_report_various_currencies(self):
        """
        Test the currency conversion when selling a timesheet product in a currency
        different than the company's one.
        """
        self.employee_user.hourly_cost = 10
        foreign_currency = self.env['res.currency'].create({
            'name': 'Fake Euro',
            'symbol': 'F€',
            'rounding': 0.01,
            'rate_ids': [
                Command.create({'name': '2020-01-01', 'rate': 2}),  # 2F€ = $1
            ]
        })
        pricelist = self.env['product.pricelist'].create({
            'name': 'Foreign Pricelist',
            'currency_id': foreign_currency.id,
            'item_ids': [
                Command.create({
                    'compute_price': 'fixed',
                    'fixed_price': 100.0,  # 100F€ = $50
                    'min_quantity': 0,
                    'applied_on': '1_product',
                    'product_id': self.product_delivery_timesheet2.id,
                })
            ],
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'pricelist_id': pricelist.id,
        })
        so_line = self.env['sale.order.line'].create({
            'product_id': self.product_delivery_timesheet2.id,
            'product_uom_qty': 1,
            'order_id': sale_order.id,
        })
        sale_order.action_confirm()
        task = self.env['project.task'].search([('sale_line_id', '=', so_line.id)])
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 1,
            'employee_id': self.employee_user.id,
            'so_line': so_line.id,
            'order_id': sale_order.id,
        })
        self.env.flush_all()
        report = self.env['timesheets.analysis.report'].browse(timesheet.id)
        self.assertEqual(report.timesheet_revenues, 50)
        self.assertEqual(report.margin, 40)   # Revenues ($50) - Employee's hourly cost ($10)
