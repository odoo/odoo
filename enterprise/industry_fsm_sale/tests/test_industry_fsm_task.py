# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import tagged
from .common import TestFsmFlowSaleCommon
from odoo import Command


@tagged('-at_install', 'post_install')
class TestIndustryFsmTask(TestFsmFlowSaleCommon):

    def test_partner_id_follows_so_shipping_address(self):
        """ For fsm tasks linked to a sale order, the partner_id should be the same as
            the partner_shipping_id set on the sale sale order.
        """
        self.env.user.groups_id += self.env.ref('account.group_delivery_invoice_address')
        so = self.env['sale.order'].create([{
            'name': 'Test SO linked to fsm task',
            'partner_id': self.partner_1.id,
        }])
        sol = self.env['sale.order.line'].create([{
            'name': 'Test SOL linked to a fsm tasl',
            'order_id': so.id,
            'task_id': self.task.id,
            'product_id': self.service_product_delivered.id,
            'product_uom_qty': 3,
        }])
        self.task.sale_line_id = sol
        partner_2 = self.env['res.partner'].create({'name': 'A Test Partner 2'})

        # 1. Modyfing shipping address on SO should update the customer on the task
        self.assertEqual(so.partner_id, self.partner_1)
        self.assertEqual(so.partner_shipping_id, self.partner_1)
        self.assertEqual(self.task.partner_id, self.partner_1)

        so.partner_shipping_id = partner_2

        self.assertEqual(so.partner_id, self.partner_1)
        self.assertEqual(so.partner_shipping_id, partner_2)
        self.assertEqual(self.task.partner_id, partner_2,
                         "Modifying the shipping partner on a sale order linked to a fsm task should update the partner of this task accordingly")

        # 2. partner_id should be False for task not billable
        self.task.project_id.allow_billable = False
        so.partner_shipping_id = partner_2
        self.assertFalse(self.task.partner_id, "Partner id should be set to False for non-billable tasks")

    def test_fsm_task_under_warranty(self):
        """ Ensure that the product price is zero in the sales order line for task is under warranty.
                Test Case:
                =========
                1. Create a task and add timesheet line to it
                2. Set the task under warranty
                3. Validate the task
                4. Check the price unit of the sale order line
        """
        self.task.write({'under_warranty': True, 'partner_id': self.partner_1.id})
        self.env['account.analytic.line'].create({
            'name': 'Timesheet',
            'task_id': self.task.id,
            'unit_amount': 0.25,
            'date': '2024-04-22',
            'employee_id': self.employee_user2.id,
        })
        self.task.action_fsm_validate()
        self.assertEqual(self.task.sale_line_id.price_unit, 0.0, "If task is under warranty, the price of the sale order line should be 0.0")

    def test_fsm_task_sale_line_id(self):
        """Ensure that no Sale Order is generated on task if task is under warranty
            and there are timesheets but no product on the task.
                Test Case:
                =========
                1. Create a task and add timesheet line to it
                2. Set the task under warranty
                3. Validate the task without any product
                4. Sale order should not be generated
        """
        self.task.write({'under_warranty': True, 'partner_id': self.partner_1.id})
        self.env['account.analytic.line'].create({
            'name': 'Timesheet',
            'task_id': self.task.id,
            'unit_amount': 0.50,
            'date': '2024-07-07',
            'employee_id': self.employee_user2.id,
        })
        self.task.action_fsm_validate()
        self.assertFalse(self.task.sale_order_id, 'Sale order should not be generated on the task.')
        self.assertFalse(self.task.timesheet_ids.so_line, 'The timesheet should not be linked to a SOL.')

    def test_fsm_task_timesheet_uses_customer_pricelist(self):
        """Test that the timesheet service line uses the fixed price from the customer's assigned pricelist.

            Steps to reproduce:
            - Create a fixed-price pricelist that applies to all products.
            - Assign the pricelist to the customer.
            - Create a task linked to that customer.
            - Add a timesheet entry to the task.
            - Mark the task as done.
            - Verify that the price of the timesheet service line in the sale order matches the fixed price from the pricelist.
        """
        pricelist = self.env['product.pricelist'].create({
            'name': 'Price List',
            'currency_id': self.env.company.currency_id.id,
            'item_ids': [Command.create({
                'applied_on': '3_global',
                'compute_price': 'fixed',
                'fixed_price': 0.0,
            })],
        })

        self.partner.property_product_pricelist = pricelist
        self.task.partner_id = self.partner
        self.env['account.analytic.line'].create({
            'employee_id': self.employee_user2.id,
            'task_id': self.task.id,
            'unit_amount': 2.0,
            'date': '2025-06-17',
        })

        self.task.action_fsm_validate()
        self.assertEqual(
            self.task.sale_line_id.price_unit,
            pricelist.item_ids[0].fixed_price,
            "The service price does not match the fixed price defined in the customer's pricelist."
        )

    def test_warranty_status_updates_sale_order_line_price(self):
        """
        Ensure that the product price is zero in the sales order line
        when the task is under warranty.
            Test Case:
            ==========
            1. Create a sales order linked to the customer.
            2. Assign a customer (partner) to the task and link the task to the sales order.
            3. Create a sales order line for a product and link it to the task.
            4. Verify the price unit matches the product's list price by default.
            5. Set the task as under warranty.
            6. Verify the price unit is set to 0.0 in the sales order line.
            7. Unset the warranty status.
            8. Verify the price unit returns to the product's list price.
        """
        so = self.env['sale.order'].create([{
            'name': 'Test SO linked to fsm task',
            'partner_id': self.partner_1.id,
        }])
        self.task.write({'partner_id': self.partner_1.id, 'sale_order_id': so})
        sol = self.env['sale.order.line'].create([{
            'name': 'Test SOL linked to a fsm tasl',
            'order_id': so.id,
            'task_id': self.task.id,
            'product_id': self.consu_product_delivered.id,
            'product_uom_qty': 3,
        }])

        self.assertEqual(sol.price_unit, self.consu_product_delivered.list_price,
                         "The price should match the product's listed price.")
        self.task.under_warranty = True
        self.assertEqual(sol.price_unit, 0.0,
                         "If task is under warranty, the price of the sale order line should be 0.0")
        self.task.under_warranty = False
        self.assertEqual(sol.price_unit, self.consu_product_delivered.list_price,
                         "The price should match the product's listed price.")

    def test_no_double_discount_for_fsm_task(self):
        """
        Test that the timesheet service line only gives discount
        once from the customer's assigned pricelist.

            Steps to reproduce:
            - Enable discounts
            - Create a discount pricelist that applies to all products.
            - Assign the pricelist to the customer.
            - Create a task linked to that customer.
            - Add a timesheet entry to the task.
            - Mark the task as done.
            - Verify that the price of the timesheet service line
            in the sale order does not have discount applied twice.
        """
        self.env.user.groups_id += self.env.ref('sale.group_discount_per_so_line')

        pricelist = self.env['product.pricelist'].create({
            'name': 'Price List',
            'item_ids': [Command.create({
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 10,
            })],
        })
        self.partner.property_product_pricelist = pricelist
        self.task.partner_id = self.partner

        analytic_line = self.env['account.analytic.line'].create({
            'employee_id': self.employee_user2.id,
            'task_id': self.task.id,
            'unit_amount': 1.0,
            'date': '2025-06-17',
        })
        self.task.action_fsm_validate()
        discounted_price = pricelist._get_product_price(
            self.task.timesheet_product_id, analytic_line.unit_amount
        )
        self.assertEqual(self.task.sale_line_id.price_subtotal, discounted_price)
