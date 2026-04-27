# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, Command
from odoo.tests import new_test_user, tagged

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('-at_install', 'post_install')
class TestSubscriptionTask(TestSubscriptionCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.config.settings'].create({
            'group_project_recurring_tasks': True,
        }).execute()

        cls.env.user.groups_id += cls.env.ref('project.group_project_recurring_tasks')
        cls.project = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Project',
            'type_ids': [
                Command.create({'name': 'a'}),
                Command.create({'name': 'b'}),
            ],
            'allow_billable': True,
        })

        cls.product_no_recurrence, cls.product_recurrence = cls.env['product.template'].create([{
            'name': 'Product No Recurrence',
            'type': 'service',
            'project_id': cls.project.id,
            'service_tracking': 'task_global_project',
        }, {
            'name': 'Product Recurrence',
            'recurring_invoice': True,
            'type': 'service',
            'project_id': cls.project.id,
            'service_tracking': 'task_global_project',
        }])

    def test_task_recurrence(self):
        Order = self.env['sale.order']
        OrderLine = self.env['sale.order.line']
        for product in [
            self.product_no_recurrence,
            self.product_recurrence,
        ]:
            is_recurrent = product.recurring_invoice
            for end_date in fields.Date.today() + relativedelta(months=1), False:
                order = Order.create({
                    'is_subscription': True,
                    'note': "original subscription description",
                    'partner_id': self.partner.id,
                    **({
                        'plan_id': self.plan_month.id,
                        'end_date': end_date,
                    } if is_recurrent else {}),
                })
                order_line = OrderLine.create({
                    'order_id': order.id,
                    'product_id': product.product_variant_id.id,
                })
                order.action_confirm()
                self.assertEqual(order_line.task_id.recurring_task, is_recurrent,
                    "The task created should be recurrent if and only if the product is recurrent")
                if not is_recurrent:
                    continue
                task_recurrence = order_line.task_id.recurrence_id
                if end_date:
                    self.assertEqual(task_recurrence.repeat_type, 'until',
                        "A subscription with an end date must create a task with a recurrence of type 'until'")
                    self.assertEqual(task_recurrence.repeat_until, end_date,
                        "A subscription with an end date must set its end date on its task's recurrence")
                else:
                    self.assertEqual(task_recurrence.repeat_type, 'forever',
                        "No end date on the subscription must result in a task with a recurrence of type 'forever'")

    def test_task_plan_close(self):
        order = self.env['sale.order'].create({
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.partner.id,
        })
        order_line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_recurrence.product_variant_id.id,
        })

        order.action_confirm()
        task = order_line.task_id
        self.assertTrue(task.recurring_task, "Task should be recurrent")
        self.assertTrue(task.recurrence_id, "Task should be recurrent")

        order.set_close()
        self.assertFalse(task.recurring_task, "Closing a subscription must stop the task recurrence")
        self.assertFalse(task.recurrence_id, "Closing a subscription must stop the task recurrence")

    def test_task_plan_cancel(self):
        order = self.env['sale.order'].create({
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.partner.id,
        })
        order_line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_recurrence.product_variant_id.id,
        })

        order.action_confirm()
        task = order_line.task_id
        self.assertTrue(task.recurring_task, "Task should be recurrent")
        self.assertTrue(task.recurrence_id, "Task should be recurrent")

        order._action_cancel()
        self.assertFalse(task.recurring_task, "Cancelling a subscription must stop the task recurrence")
        self.assertFalse(task.recurrence_id, "Cancelling a subscription must stop the task recurrence")

    def test_task_plan_quotation_template(self):
        order = self.env['sale.order'].create({
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.partner.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        order_line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_recurrence.product_variant_id.id,
        })

        order.action_confirm()
        task_recurrence = order_line.task_id.recurrence_id
        self.assertEqual(task_recurrence.repeat_type, 'until',
            "As the subscription template is of type 'limited', the task recurrence should be of type 'until'")
        self.assertEqual(task_recurrence.repeat_until.month, order.end_date.month,
            "The task recurrence should end on the same month as the subscription")

    def test_task_plan_upsell(self):
        product_plan_2 = self.env['product.template'].create({
            'name': 'Product Recurrence 2',
            'recurring_invoice': True,
            'type': 'service',
            'project_id': self.project.id,
            'service_tracking': 'task_global_project',
        })
        order = self.env['sale.order'].create({
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.partner.id,
            "end_date": fields.Date.today() + relativedelta(months=1),
        })
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_recurrence.product_variant_id.id,
        })

        order.action_confirm()
        order._create_recurring_invoice()
        action = order.prepare_upsell_order()
        upsell = self.env['sale.order'].browse(action['res_id'])

        upsell.order_line.filtered(lambda sol: not sol.display_type).product_uom_qty = 1
        upsell.order_line += self.env['sale.order.line'].create({
            'order_id': upsell.id,
            'product_id': product_plan_2.product_variant_id.id,
        })
        upsell.action_confirm()
        recurrences = order.order_line.task_id.recurrence_id
        self.assertTrue(all(recurrences.mapped(lambda r: r.repeat_type == 'until')))
        self.assertTrue(all(recurrences.mapped(lambda r: r.repeat_until.month == order.end_date.month)))

    def test_task_generation(self):
        product_task = self.env['product.template'].create({
            'name': 'Product task',
            'type': 'service',
            'recurring_invoice': True,
            'project_id': self.project.id,
            'service_tracking': 'task_global_project',
        })
        order = self.env['sale.order'].create({
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.partner.id,
        })
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product_task.product_variant_id.id,
        })

        order.action_confirm()
        self.assertEqual(len(order.tasks_ids), 1, "One task should be created")
        order._create_recurring_invoice()
        action = order.prepare_upsell_order()
        upsell = self.env['sale.order'].browse(action['res_id'])

        upsell.order_line[:1].product_uom_qty = 1
        upsell.action_confirm()
        self.assertEqual(len(order.tasks_ids), 1, "No additional task should be created")
        action = order.prepare_renewal_order()
        renew = self.env['sale.order'].browse(action['res_id'])

        renew.order_line[:1].product_uom_qty = 2
        renew.action_confirm()
        self.assertEqual(len(renew.tasks_ids), 1, "One task for renew should be created")

    def test_recurring_task_generation_portal(self):
        order = self.env['sale.order'].create({
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.partner.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        order_line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_recurrence.product_variant_id.id,
        })

        order.with_user(self.user_portal).sudo().action_confirm()
        self.assertEqual(len(order_line.task_id.recurrence_id), 1)

        self.env['res.config.settings'].create({
            'group_project_recurring_tasks': False,
        }).execute()

        order = order.copy()
        order.with_user(self.user_portal).sudo().action_confirm()
        self.assertEqual(len(order_line.task_id.recurrence_id), 0)

    def test_task_creation_on_non_recurring_product_upsell(self):
        subscription = self.env['sale.order'].create({
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.partner.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })

        self.env['sale.order.line'].create([{
            'order_id': subscription.id,
            'product_id': self.product_recurrence.product_variant_id.id,
        }])

        subscription.action_confirm()
        invoice = subscription._create_invoices(final=True)
        invoice.action_post()
        task_domain = [('project_id', '=', self.project.id)]
        self.assertEqual(len(self.env['project.task'].search(task_domain)), 1, 'Task should be created')

        action = subscription.prepare_upsell_order()
        upsell = self.env['sale.order'].browse(action['res_id'])

        upsell.order_line.filtered(lambda sol: not sol.display_type).product_uom_qty = 1
        self.env['sale.order.line'].create([{
            'order_id': upsell.id,
            'product_id': self.product_no_recurrence.product_variant_id.id,
        }])

        upsell.action_confirm()
        tasks = self.env['project.task'].search(task_domain)
        self.assertEqual(len(tasks), 2, 'Task should only be created on upsell if the product is non-recurring')
        self.assertTrue(self.product_no_recurrence.name in tasks[0].name)

    def test_confirm_subscription_with_recurring_service_product_as_sale_manager(self):
        """
            Steps:
                1. Create a user with Sale Manager access.
                2. Create a subscription-based sale order as that user.
                3. Add a recurring service product to the order line.
                4. Confirm the sale order to trigger task creation with recurrence.
        """

        user_salemanager = new_test_user(self.env, login='user_salemanager', groups='sales_team.group_sale_manager')

        sale_order = self.env['sale.order'].with_user(user_salemanager).create({
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'partner_id': self.partner.id,
        })
        order_line = self.env['sale.order.line'].with_user(user_salemanager).create({
            'order_id': sale_order.id,
            'product_id': self.product_recurrence.product_variant_id.id,
        })

        sale_order.with_user(user_salemanager).action_confirm()
        self.assertEqual(len(order_line.task_id.recurrence_id), 1)
