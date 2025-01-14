# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo import Command
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestSaleTimesheetMargin(TestCommonSaleTimesheet):

    def setUp(self):
        super().setUp()
        uom_day_id = self.ref('uom.product_uom_day')
        self.uom_day = self.env['uom.uom'].browse(uom_day_id)
        self.product_1 = self.env['product.product'].create({
            'name': "Service Ordered, create no task, uom day",
            'list_price': 1.0,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_day_id,
            'default_code': 'SERV-ORDERED-DAY',
            'service_type': 'timesheet',
            'service_tracking': 'task_in_project',
            'project_id': False,
            'taxes_id': False,
        })
        self.employee_manager.hourly_cost = 10

    def test_sale_timesheet_margin(self):
        """ Test the timesheet cost is reported correctly in sale order line. """
        sale_order = self.env['sale.order'].create({
            'name': 'Test_SO0001',
            'order_line': [
                Command.create({
                    'product_id': self.product_1.id,
                    'price_unit': 1.0,
                    'product_uom_id': self.uom_day.id,
                    'product_uom_qty': 1.0,
            })],
            'partner_id': self.partner_b.id,
            'partner_invoice_id': self.partner_b.id,
            'partner_shipping_id': self.partner_b.id,
        })
        # Confirm the sales order, create project and task.
        sale_order.action_confirm()

        # Add timesheet line
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'unit_amount': 2,
            'employee_id': self.employee_manager.id,
            'project_id': sale_order.project_ids.id,
            'task_id': sale_order.order_line.task_id.id,
            'account_id': self.analytic_account_sale.id,
            'so_line': sale_order.order_line.id,
        })
        sale_order.order_line._compute_purchase_price()
        # Cost is expressed in SO line uom
        expected_cost = self.uom_day._compute_quantity(
            self.employee_manager.hourly_cost,
            self.env.company.project_time_mode_id
        )
        self.assertEqual(sale_order.order_line.purchase_price, expected_cost, "Sale order line cost should be number of working hours on one day * timesheet cost of the employee set on the timesheet linked to the SOL.")
