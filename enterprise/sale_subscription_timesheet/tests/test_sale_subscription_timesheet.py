# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged, freeze_time

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestSubscriptionTask(TestSubscriptionCommon, TestCommonSaleTimesheet):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.product_deliver_timesheet = self.env['product.product'].create({
            'name': "Service Ordered, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.uom_hour.id,
            'uom_po_id': self.uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_type': 'timesheet',
            'recurring_invoice': True,
            'service_tracking': 'task_global_project',
            'project_id': self.project_global.id,
            'taxes_id': False,
            'property_account_income_id': self.account_sale.id,
        })
        self.subscription_timesheet = self.env['sale.order'].create({
            'name': 'TestSubscriptionWithTimeSheet',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
             'order_line': [
                    Command.create({
                        'product_id': self.product_deliver_timesheet.id,
                        'product_uom_qty': 1
                    }),
                ],
        })

    def test_sub_timesheet_create_recurring_tasks(self):
        # Similar test with recurring tasks: new tasks are created automatically
        # Note: when the setting is deactivated it works similarly. All timesheets must be created into a single task.
        self.env['res.config.settings'].create({
            'group_project_recurring_tasks': True,
        }).execute()

        self.env.user.groups_id += self.env.ref('project.group_project_recurring_tasks')
        with freeze_time("2024-10-01"):
            self.subscription_timesheet.action_confirm()
            task = self.subscription_timesheet.tasks_ids
            self.assertTrue(task, "A new task should be created")
            # after confirming the subscription, next invoice date is set to the next period
            self.assertEqual(self.subscription_timesheet.order_line.qty_delivered, 0, "No delivery before creating the first recurring invoice")
            # after creating timesheet line quantity delivered set to 4
            self.env['account.analytic.line'].create({
                'name': 'Test Line',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 4,
                'employee_id': self.employee_user.id,
            })
            self.assertEqual(self.subscription_timesheet.order_line.qty_delivered, 4, "Product should be delivered after creating the recurring invoice")
        with freeze_time("2024-10-01"):
            # record timesheet for that task
            self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 6,
            'employee_id': self.employee_user.id,
             })
            self.subscription_timesheet.order_line.with_context(arj=True)._compute_qty_delivered()
            self.assertEqual(self.subscription_timesheet.order_line.qty_delivered, 10, "The product should be delivered")
            # When the task is done, we create a new one
            task.state = '1_done'
            self.subscription_timesheet.invalidate_recordset(['tasks_ids'])
            task = self.subscription_timesheet.tasks_ids - task
            self.assertTrue(task)
        with freeze_time("2024-11-01"):
            inv = self.subscription_timesheet._create_recurring_invoice()
            self.assertEqual(inv.amount_untaxed, 900, "The amount depends on the timesheet (90 per hour)")
        with freeze_time("2024-11-15"):
            self.env['account.analytic.line'].create({
                'name': 'Test Line',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 50,
                'employee_id': self.employee_user.id,
             })
            self.assertEqual(self.subscription_timesheet.order_line.qty_delivered, 50, "The product should be delivered")
        with freeze_time("2024-12-01"):
            inv = self.subscription_timesheet._create_recurring_invoice()
            # When the task is done, we create a new one
            task.state = '1_done'
            self.subscription_timesheet.invalidate_recordset(['tasks_ids'])
            task = self.subscription_timesheet.tasks_ids - task
            self.assertTrue(task)
            self.assertEqual(inv.amount_untaxed, 4500, "The amount depends on the timesheet (90 per hour)")
            self.assertEqual(len(task), 2, "Two tasks are created automatically")

    def test_sub_timesheet_order_invoice_product(self):
        # Subscription service product with invoicing policy `ordered_prepaid`
        self.product_order_timesheet2.recurring_invoice = True

        with freeze_time("2025-02-15"):
            subscription_timesheet = self.env['sale.order'].create({
                'name': 'Test',
                'plan_id': self.plan_month.id,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'start_date': '2025-02-01',
                'order_line': [
                    Command.create({
                        'product_id': self.product_order_timesheet2.id,
                        'product_uom_qty': 10
                    }),
                ],
            })
            subscription_timesheet.action_confirm()
            task = subscription_timesheet.tasks_ids
            self.env['account.analytic.line'].create([
                {
                    'name': 'Timesheet before subscription period',
                    'project_id': task.project_id.id,
                    'task_id': task.id,
                    'unit_amount': 2,
                    'employee_id': self.employee_user.id,
                    'date': '2025-01-15'
                },
                {
                    'name': 'Timesheet during subscription period',
                    'project_id': task.project_id.id,
                    'task_id': task.id,
                    'unit_amount': 2,
                    'employee_id': self.employee_user.id,
                    'date': '2025-02-15'
                },
            ])
            # We need to run the cron once in order to update the next_invoice_date of the subscription
            self.env['sale.order']._cron_recurring_create_invoice()
            self.assertEqual(subscription_timesheet.order_line.qty_delivered, 2, "2 hours delivered for the February period")

    @freeze_time("2025-03-03")
    def test_sub_invoice_timesheet(self):
        self.subscription_timesheet.action_confirm()
        task = self.subscription_timesheet.tasks_ids
        _, present_timesheet = self.env['account.analytic.line'].create([
            {
                'name': 'Test Line',
                'date': '2025-02-01',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 3,
                'employee_id': self.employee_user.id,
            },
            {
                'name': 'Test Line',
                'date': '2025-03-03',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 4,
                'employee_id': self.employee_user.id,
            },
        ])
        self.subscription_timesheet._create_recurring_invoice()

        self.assertTrue(self.subscription_timesheet.last_invoice_date)
        moves = self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [self.subscription_timesheet.id],
            'active_id': self.subscription_timesheet.id,
        }).create({
            'advance_payment_method': 'delivered'
        }).create_invoices()

        invoice = self.env['account.move'].browse(moves['res_id'])
        self.assertEqual(len(invoice.timesheet_ids), 1)
        self.assertEqual(invoice.invoice_line_ids.quantity, present_timesheet.unit_amount)
        self.assertEqual(invoice.timesheet_ids.id, present_timesheet.id)

    @freeze_time("2025-08-03")
    def test_sub_link_timesheet_to_invoice(self):
        subscription = self.env['sale.order'].create({
            'name': 'CopyTestSubscriptionWithTimeSheet',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [
                    Command.create({
                        'product_id': self.product_deliver_timesheet.id,
                        'product_uom_qty': 6
                    }),
                ],
            'start_date': '2025-07-01',
        })
        subscription.action_confirm()
        subscription.write({'next_invoice_date': '2025-08-01'})

        task = subscription.tasks_ids
        self.env['account.analytic.line'].create([
            {
                'name': 'Test Include Line',
                'date': '2025-07-01',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 3,
                'employee_id': self.employee_user.id,
            },
            {
                'name': 'Test Line',
                'date': '2025-07-31',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 3,
                'employee_id': self.employee_user.id,
            },
            {
                'name': 'Test Exclude Line',
                'date': '2025-08-01',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 4,
                'employee_id': self.employee_user.id,
            },
        ])

        moves = self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [subscription.id],
            'active_id': subscription.id,
        }).create({
            'advance_payment_method': 'delivered'
        }).create_invoices()
        invoice = self.env['account.move'].browse(moves['res_id'])

        self.assertEqual(len(invoice.timesheet_ids), 2)

    @freeze_time("2025-08-03")
    def test_invoice_orders_if_delivery_qty(self):
        """
        Test invoicing order that has lines with delivery invoicing policy products
        and has delivered quantity
        """
        subscription = self.env['sale.order'].create({
            'name': 'CopyTestSubscriptionWithTimeSheet',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [
                Command.create({
                    'product_id': self.product_deliver_timesheet.id,
                    'product_uom_qty': 0
                }),
            ],
            'start_date': '2025-07-01',
        })
        subscription.action_confirm()
        subscription.write({'next_invoice_date': '2025-08-01'})

        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project_global.id,
            'sale_order_id': subscription.id,
            'sale_line_id': subscription.order_line[0].id,
        })
        timesheet = self.env['account.analytic.line'].create([
            {
                'name': 'Test Include Line',
                'date': '2025-07-15',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 3,
                'employee_id': self.employee_user.id,
            },
        ])

        self.env['sale.order']._cron_recurring_create_invoice()

        # An invoice should be created
        self.assertTrue(subscription.invoice_ids)
        self.assertEqual(subscription.invoice_ids.invoice_line_ids[0].quantity, timesheet.unit_amount)
