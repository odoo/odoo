# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from .common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestUpsellWarning(TestCommonSaleTimesheet):
    def test_display_upsell_warning(self):
        """ Test to display an upsell warning


            We display an upsell warning in SO when this following condition is satisfy in its SOL:
            (qty_delivered / product_uom_qty) >= product_id.service_upsell_threshold

            Test Case:
            =========
            1) Configure the upsell warning in prepaid service product
            2) Create SO with a SOL containing this updated product,
            3) Create Project and Task,
            4) Timesheet in the task to satisfy the condition for the SOL to display an upsell warning,
            5) Check if the SO has an 'sale.mail_act_sale_upsell' activity.
        """
        # 1) Configure the upsell warning in prepaid service product
        self.product_order_timesheet1.write({
            'service_upsell_threshold': 0.5,
        })

        # 2) Create SO with a SOL containing this updated product
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
        })

        self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_order_timesheet1.id,
            'product_uom_qty': 10,
        })
        so.action_confirm()

        # 3) Create Project and Task
        project = self.env['project.project'].create({
            'name': 'Project',
            'allow_timesheets': True,
            'allow_billable': True,
            'partner_id': self.partner_a.id,
            'analytic_account_id': self.analytic_account_sale.id,
        })
        task = self.env['project.task'].create({
            'name': 'Task Test',
            'project_id': project.id,
        })
        task._compute_sale_line()

        # 4) Timesheet in the task to satisfy the condition for the SOL to display an upsell warning
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'unit_amount': 5,
            'employee_id': self.employee_manager.id,
            'project_id': project.id,
            'task_id': task.id,
        })
        timesheet._compute_so_line()
        so.order_line._compute_qty_delivered()
        so.order_line._compute_invoice_status()
        so._compute_invoice_status()
        # Normally this method is called at the end of _compute_invoice_status and other compute method. Here, we simulate for invoice_status field
        so._compute_field_value(so._fields['invoice_status'])

        self.assertEqual(len(so.activity_search(['sale.mail_act_sale_upsell'])), 0, 'No upsell warning should appear in the SO.')
        timesheet.write({
            'unit_amount': 6,
        })
        timesheet._compute_so_line()
        so.order_line._compute_qty_delivered()
        so.order_line._compute_invoice_status()
        so._compute_invoice_status()
        # Normally this method is called at the end of _compute_invoice_status and other compute method. Here, we simulate for invoice_status field
        so._compute_field_value(so._fields['invoice_status'])

        # 5) Check if the SO has an 'sale.mail_act_sale_upsell' activity.
        self.assertEqual(len(so.activity_search(['sale.mail_act_sale_upsell'])), 1, 'A upsell warning should appear in the SO.')
