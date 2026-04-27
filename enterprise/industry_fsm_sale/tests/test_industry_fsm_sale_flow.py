# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from odoo import Command
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged, Form, new_test_user
from odoo.tools.float_utils import float_compare


@tagged('-at_install', 'post_install')
class TestFsmFlowSale(TestFsmFlowSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.task.partner_id = cls.partner_1

    def test_invoicing_flow(self):
        self.service_product_ordered.write({
            'type': 'service',
            'service_policy': 'ordered_prepaid',
        })
        self.service_product_delivered.write({
            'type': 'service',
            'service_policy': 'delivered_timesheet',
        })

        self.fsm_project.write({
            'timesheet_product_id': self.service_product_delivered.id,
        })

        self.assertFalse(self.task.sale_order_id)
        self.assertFalse(self.task.sale_line_id)
        self.assertFalse(self.task.task_to_invoice)
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).set_fsm_quantity(1.0)
        self.assertEqual(len(self.task.sale_order_id.order_line), 1)

        first_order_line = self.task.sale_order_id.order_line
        self.assertEqual(first_order_line.product_uom_qty, 1.0)
        self.assertFalse(self.task.display_create_invoice_primary)
        self.assertFalse(self.task.sale_line_id)

        self.task.sale_order_id.write({
            'order_line': [
                Command.create({
                    'product_id': self.service_timesheet.id,
                    'product_uom_qty': 1.0,
                    'name': '/',
                }),
            ]
        })

        if self.task.sale_order_id.state != 'sale':
            self.task.sale_order_id.action_confirm()
        self.assertEqual(len(self.task.sale_order_id.order_line), 2)
        service_timesheet_order_line = self.task.sale_order_id.order_line.filtered(lambda order_line: order_line.product_id == self.service_timesheet)
        self.task.write({
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'unit_amount': 0.5,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
                Command.create({
                    'name': '/',
                    'unit_amount': 0.5,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
                Command.create({
                    'name': '/',
                    'unit_amount': 1.0,
                    'so_line': service_timesheet_order_line.id,
                    'is_so_line_edited': True,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
            ]
        })

        self.task.action_fsm_validate()
        self.assertEqual(len(self.task.timesheet_ids.so_line), 2)
        self.assertEqual(self.task.sale_order_id.order_line.mapped('qty_delivered'), [1.0] * 3)
        self.assertEqual(self.task.sale_line_id.product_id, self.service_product_delivered)
        self.assertEqual(self.task.sale_order_id.state, 'sale')
        self.assertEqual(len(self.task.sale_order_id.order_line), 3)
        second_order_line = self.task.sale_line_id
        self.assertEqual(second_order_line.project_id, self.fsm_project)
        self.assertEqual(second_order_line.task_id, self.task)
        self.assertTrue(second_order_line.is_service)
        self.assertEqual(second_order_line.qty_delivered_method, 'timesheet')

        self.assertTrue(self.task.task_to_invoice)
        self.assertTrue(self.task.display_create_invoice_primary)
        self.task.sale_order_id._create_invoices()
        self.assertEqual(self.task.invoice_count, 1)
        self.assertFalse(self.task.display_create_invoice_primary)

        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertTrue(self.task.display_create_invoice_primary)
        self.task.sale_order_id._create_invoices()
        self.assertEqual(self.task.invoice_count, 2)
        self.assertFalse(self.task.display_create_invoice_primary)

    def test_invoice_fsm_task_with_diff_shipping_address(self):
        """
        When the shipping address is different from the invoice address,
        the task should be able to be invoiced once done.
        """
        # activate setting for splitting the invoice and shipping address
        config = self.env['res.config.settings'].create({
            'group_sale_delivery_address': True,
        })
        config.execute()
        fsm_product = self.env['product.product'].create({
            'name': 'Fsm Product',
            'type': 'service',
            'list_price': 100,
            'service_policy': 'ordered_prepaid',
            'project_id': self.fsm_project.id,
            'service_tracking': 'task_global_project',
        })
        billing_partner, shipping_partner = self.env['res.partner'].create([{
            'name': 'Billing Partner',
        }, {
            'name': 'Shipping Partner',
        }])
        sale_order = self.env['sale.order'].create({
            'partner_id': billing_partner.id,
            'partner_invoice_id': billing_partner.id,
            'partner_shipping_id': shipping_partner.id,
        })
        sale_order.order_line = self.env['sale.order.line'].create([{
            'product_id': fsm_product.id,
            'product_uom_qty': 1.0,
            'order_id': sale_order.id,
        }])
        sale_order.action_confirm()
        self.assertEqual(len(sale_order.tasks_ids), 1, "We should have 1 task after confirming the SO.")
        task = sale_order.tasks_ids[0]
        self.assertEqual(task.partner_id.commercial_partner_id, shipping_partner,
                         "Partner on the task should be the shipping address.")
        self.assertEqual(task.sale_order_id, sale_order, "The sale order should be linked to the task.")
        task.action_fsm_validate()
        self.assertTrue(task.task_to_invoice, "Task should be invoiceable")

    def test_task_sale_order_id_and_sale_order_line_id_consistency(self):
        sale_order_1 = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_delivery_timesheet1.id,
                    'product_uom_qty': 10,
                })
            ]
        })
        sale_order_1.action_confirm()

        task = self.env['project.task'].with_context({
            'default_project_id': self.fsm_project_employee_rate.id,
        }).create({
            'sale_line_id': sale_order_1.order_line.id,
            'name': 'Test Task',
        })

        self.assertEqual(task.sale_order_id.id, sale_order_1.id)

        sale_order_2 = sale_order_1.copy()

        task.write({
            'sale_line_id': sale_order_2.order_line.id,
        })

        self.assertEqual(task.sale_order_id.id, sale_order_2.id)

    def test_qty_to_invoice_from_fsm(self):
        """
        Check that sale order lines coming from an fsm task and for a product with a price of zero
        are not going to be invoiced.
        """
        product = self.product_a.with_context({'fsm_task_id': self.task.id})
        product.set_fsm_quantity(2)
        so = self.task.sale_order_id
        if so.state == 'draft':
            so.action_confirm()  # needed if stock is not installed
        sol = so.order_line[-1]
        self.assertEqual(sol.qty_to_invoice, 2.0)

        so_form = Form(so)
        with so_form.order_line.edit(0) as line:
            line.price_unit = 0.0
        so_form.save()
        self.assertEqual(sol.qty_to_invoice, 2.0, "Anglo Saxon Accounting should be enable")

        with so_form.order_line.edit(0) as line:
            line.price_unit = 0.01
        so_form.save()
        self.assertEqual(sol.qty_to_invoice, 2.0, "$0.01 shouldn't count as free")
        self.env.company.anglo_saxon_accounting = False
        with so_form.order_line.edit(0) as line:
            line.price_unit = 0.00
        so_form.save()
        self.assertEqual(sol.qty_to_invoice, 0.0, "Anglo Saxon Accounting should be disable")

    def test_uom_conversion_fsm_task_to_so(self):
        """Checks that the hours recorded on Timesheets are converted to the correct UOM on the Sales Order"""

        working_time = self.env['uom.category'].search([('name', '=', 'Working Time')])
        quarter_hour = self.env['uom.uom'].create({
            'name': 'Quarter-Hours',
            'category_id': working_time.id,
            'ratio': 32.0,
            'uom_type': 'smaller',
        })
        self.service_timesheet._inverse_service_policy()  # trigger value changes for invoice policy and service_type
        self.service_timesheet.uom_id = quarter_hour
        self.service_timesheet.list_price = 40
        self.fsm_project.sale_line_employee_ids = [Command.create({
            'employee_id': self.employee_user2.id,
            'timesheet_product_id': self.service_timesheet.id,
            'price_unit': 40,
        })]
        field_task = self.env['project.task'].create({
            'name': 'Field Task',
            'project_id': self.fsm_project.id,
            'timesheet_ids': [Command.create({
                'employee_id': self.employee_user2.id,
                'name': '/',
                'unit_amount': 1.75,  # 01:45
                'product_uom_id': self.env['uom.uom'].search([('name', '=', 'Hours')]).id
            })],
            'partner_id': self.partner_1.id,
        })
        field_task.action_fsm_validate()
        sale_order = field_task.sale_order_id
        order_lines = sale_order.order_line
        self.assertEqual(float_compare(order_lines.product_uom_qty, 7.0, precision_digits=2), 0, "The Ordered Quantities should match the Timesheets at the time of creation")

    def test_prevent_empty_sol_for_timesheet(self):
        """
        Test that when adding a product to the task and mark as done that task then,
        it does not create an empty SOL for timesheet if no timesheets are added.

        Test Case:
        =========
        1. Create a task and add a product to it
        2. Validate the task
        3. Check the sale order line should not be created for timesheet
        """
        self.fsm_project.write({
            'timesheet_product_id': self.service_timesheet.id,
        })
        self.service_product_ordered.with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.task.action_fsm_validate()
        sale_order_lines = self.env['sale.order.line'].search([('order_id', '=', self.task.sale_order_id.id)])
        self.assertEqual(len(sale_order_lines), 1)
        self.assertEqual(sale_order_lines.product_id, self.service_product_ordered)

    def test_task_sale_order_auto_fills_salesperson(self):
        """
        Check that sale order has an assigned salesperson by default when adding products to it.
        Expected behavior is: 1st assignee if any, current user if not
        """
        assignee_1 = new_test_user(self.env, login='john')
        assignee_2 = new_test_user(self.env, login='albert')

        task_no_assignee, task_with_assignee = self.env['project.task'].with_context({
            'default_project_id': self.fsm_project_employee_rate.id,
        }).create([
            {
                'name': 'No assignee',
                'partner_id': self.partner_1.id
            },
            {
                'name': 'With assignee',
                'partner_id': self.partner_1.id,
                'user_ids': [assignee_1.id, assignee_2.id],
            },
        ])

        task_no_assignee._fsm_create_sale_order()
        task_with_assignee._fsm_create_sale_order()
        self.assertEqual(task_no_assignee.sale_order_id.user_id, self.env.user)
        self.assertEqual(task_with_assignee.sale_order_id.user_id, assignee_1)

    def test_invoice_status_after_change_price_for_fully_invoiced_order(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [
                Command.create({
                    'product_id': self.consu_product_ordered.id,
                    'product_uom_qty': 10,
                })
            ]
        })

        sol = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.service_product_delivered.id,
            'product_uom_qty': 3,
            'price_unit': 40,
            'sequence': 20,
            'task_id': self.task.id
        })
        so.action_confirm()
        sol.qty_delivered = 3

        invoice = so._create_invoices()
        invoice.action_post()

        self.assertEqual(so.invoice_status, 'invoiced')
        sol.price_unit = 0
        self.assertEqual(so.invoice_status, 'invoiced')

    def test_copy_task_sale_fields(self):
        normal_project = self.env['project.project'].create({
            'name': 'Normal Project',
            'allow_billable': True,
            'allow_timesheets': True,
            'company_id': self.env.company.id,
        })
        normal_task = self.env['project.task'].create({
            'name': 'Original Task for Copy Test',
            'project_id': normal_project.id,
            'partner_id': self.partner_1.id,
            'timesheet_ids': [Command.create({
                'employee_id': self.employee_user2.id,
                'name': '/',
                'unit_amount': 1,
            })],
        })
        
        fsm_product = self.env['product.product'].create({
            'name': 'Fsm Product',
            'list_price': 100,
        })
        fsm_task = self.env['project.task'].create({
            'name': 'Original Task for Copy Test',
            'project_id': self.fsm_project.id,
            'partner_id': self.partner_1.id,
        })
        fsm_task_with_recurrence = self.env['project.task'].create({
            'name': 'Original Task for Copy Test 2',
            'project_id': self.fsm_project.id,
            'partner_id': self.partner_1.id,
            'recurring_task': True,
        })
        
        fsm_product.with_context({'fsm_task_id': fsm_task.id}).set_fsm_quantity(10.0)
        fsm_product.with_context({'fsm_task_id': normal_task.id}).set_fsm_quantity(10.0)
        fsm_product.with_context({'fsm_task_id': fsm_task_with_recurrence.id}).set_fsm_quantity(10.0)

        self.assertTrue(fsm_task.sale_order_id)
        self.assertEqual(len(fsm_task.sale_order_id.order_line), 1)

        self.assertTrue(normal_task.sale_order_id)
        self.assertEqual(len(normal_task.sale_order_id.order_line), 1)
        
        self.assertTrue(fsm_task_with_recurrence.sale_order_id)
        self.assertEqual(len(fsm_task_with_recurrence.sale_order_id.order_line), 1)

        fsm_task.action_fsm_validate()
        fsm_task.sale_order_id._create_invoices()
        
        normal_task.action_fsm_validate()
        normal_task.sale_order_id._create_invoices()
        
        fsm_task_with_recurrence.action_fsm_validate()
        fsm_task_with_recurrence.sale_order_id._create_invoices()

        self.assertTrue(fsm_task.sale_order_id.invoice_ids)
        self.assertTrue(normal_task.sale_order_id.invoice_ids)
        self.assertTrue(fsm_task_with_recurrence.sale_order_id.invoice_ids)

        fsm_task.update(fsm_task.copy_data()[0])
        normal_task.update(normal_task.copy_data()[0])
        fsm_task_with_recurrence.update(fsm_task_with_recurrence.copy_data()[0])

        self.assertFalse(fsm_task.sale_order_id)
        self.assertFalse(fsm_task.sale_order_id.invoice_ids)

        self.assertTrue(normal_task.sale_order_id)
        self.assertTrue(normal_task.sale_order_id.invoice_ids)

        self.assertTrue(fsm_task_with_recurrence.sale_order_id)
        self.assertTrue(fsm_task_with_recurrence.sale_order_id.invoice_ids)

    def test_invoice_without_sale_order(self):
        """Should return a red toast notification if no sale order is linked."""
        res = self.task.action_create_invoice()
        self.assertEqual(res['params']['type'], 'danger', "Expected a red toast notification")

    def test_invoice_status_in_anglo_saxon(self):
        self.task.partner_id = self.partner_1.id
        # Case 1: Product price is zero and Anglo-Saxon accounting is enabled.
        self.service_product_delivered.list_price = 0.0
        self.service_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        so = self.task.sale_order_id
        sol = so.order_line[0]
        if so.state == 'draft':
            so.action_confirm()  # needed if stock is not installed
        self.assertEqual(
            sol.invoice_status,
            'to invoice',
            "Invoice status should be 'to invoice' when Anglo-Saxon accounting is enabled and the price is zero."
        )
        self.assertEqual(sol.qty_to_invoice, 1.0, "Qty to invoice should be set on anglo-saxon lines")
        # Case 2: Product price is greater than zero and Anglo-Saxon accounting is enabled.
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(
            sol.invoice_status,
            'to invoice',
            "Invoice status should be 'to invoice' when the price is greater than zero."
        )
        so._create_invoices()
        self.assertEqual(
            sol.invoice_status,
            'invoiced',
            "Invoice status should be 'invoiced' when Anglo-Saxon accounting is enabled and invoice is generated."
        )
        # Case 3: Product price is zero and Anglo-Saxon accounting is disabled.
        self.env.company.anglo_saxon_accounting = False
        self.service_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(
            sol.invoice_status,
            'no',
            "Invoice status should be 'no' when Anglo-Saxon accounting is disabled and the price is zero."
        )
        # Case 4: create SO in self env company which has anglo saxon true and task company is different where anglo saxon is false
        self.env.company.anglo_saxon_accounting = True
        fsm_project_second = self.env['project.project'].create({
            'name': 'Field Service second',
            'is_fsm': True,
            'company_id': self.company_data_2['company'].id,
        })
        task_second = self.env['project.task'].create({
            'name': 'Fsm task second',
            'project_id': fsm_project_second.id,
            'partner_id': self.partner_1.id})
        self.company_data_2['company'].anglo_saxon_accounting = False
        self.service_product_delivered.list_price = 0.0
        self.service_product_delivered.with_context({'fsm_task_id': task_second.id}).fsm_add_quantity()
        self.assertEqual(
            task_second.sale_order_id.invoice_status,
            'no',
            "Invoice status should be 'no' when the task's company has Anglo-Saxon accounting disabled and the price is zero."
        )

    def test_sale_order_unlink_on_sale_item_removal(self):
        """
        When a sales order line is unlinked from a task, the sales order should also
        be unlinked, unless the task is related to FSM.
        """
        fsm_product = self.env['product.product'].create(
            {
                'name': "Fsm Product",
                'type': 'service',
                'service_policy': 'ordered_prepaid',
                'project_id': self.fsm_project.id,
                'service_tracking': 'task_global_project',
            }
        )
        self.service_timesheet.service_tracking = "task_in_project"
        sale_order, fsm_order = self.env['sale.order'].create([
            {
                'partner_id': self.partner_1.id,
                'order_line': [Command.create({'product_id': self.service_timesheet.id})]
            },
            {
                'partner_id': self.partner_1.id,
                'order_line': [Command.create({'product_id': fsm_product.id})]
            }
        ])
        (sale_order | fsm_order).action_confirm()
        self.assertEqual(len(sale_order.tasks_ids), 1)
        self.assertEqual(len(fsm_order.tasks_ids), 1)

        task = sale_order.tasks_ids
        fsm_task = fsm_order.tasks_ids
        (task | fsm_task).sale_line_id = False
        self.assertFalse(task.sale_order_id.id)
        self.assertTrue(fsm_task.sale_order_id.id)
