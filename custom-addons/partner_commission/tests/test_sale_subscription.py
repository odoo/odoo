# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo.tests.common import Form, tagged
from odoo.addons.partner_commission.tests.setup import TestCommissionsSetup
from odoo import fields


@tagged('commission_subscription', 'post_install', '-at_install')
class TestSaleSubscription(TestCommissionsSetup):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({"implied_ids": [(4, cls.env.ref('sale_management.group_sale_order_template').id)]})

    def test_referrer_commission_plan_changed(self):
        """When the referrer's commission plan changes, its new commission plan should be set on the subscription,
        unless commission_plan_frozen is checked."""
        self.referrer.commission_plan_id = self.gold_plan
        # # Normal Sale order
        form = Form(self.env['sale.order'])
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        form.sale_order_template_id = self.template_yearly
        so = form.save()

        # Auto assignation mode.
        self.referrer.commission_plan_id = self.silver_plan
        self.assertEqual(so.commission_plan_id, self.silver_plan)
        self.referrer.commission_plan_id = self.gold_plan
        self.assertEqual(so.commission_plan_id, self.gold_plan)

        # Subscriptions

        form = Form(self.env['sale.order'])
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        form.sale_order_template_id = self.template_yearly
        # Subscription plan is defined by the product and pricing
        with form.order_line.new() as line:
            line.name = self.worker.name
            line.product_id = self.worker
            line.product_uom_qty = 1
        sub = form.save()

        # Auto assignation mode.
        self.referrer.commission_plan_id = self.silver_plan
        self.assertEqual(sub.commission_plan_id, self.silver_plan)

        # Fixed mode.
        sub.commission_plan_frozen = True
        self.referrer.commission_plan_id = self.gold_plan
        self.assertEqual(sub.commission_plan_id, self.silver_plan)

    def test_referrer_grade_changed(self):
        """When the referrer's grade changes, its new commission plan should be set on the subscription,
        unless commission_plan_frozen is checked."""
        self.referrer.grade_id = self.gold
        self.referrer._onchange_grade_id()
        form = Form(self.env['sale.order'])
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        form.sale_order_template_id = self.template_yearly
        # Subscription plan is defined by the product and pricing
        with form.order_line.new() as line:
            line.name = self.worker.name
            line.product_id = self.worker
            line.product_uom_qty = 1
        sub = form.save()

        # Auto assignation mode.
        self.referrer.grade_id = self.silver
        self.referrer._onchange_grade_id()
        self.assertEqual(sub.commission_plan_id, self.silver_plan)

        # Fixed mode.
        sub.commission_plan_frozen = True
        self.referrer.grade_id = self.gold
        self.referrer._onchange_grade_id()
        self.assertEqual(sub.commission_plan_id, self.silver_plan)

    def test_sub_data_forwarded_to_renewal(self):
        """Some data should be forwarded from the subscription to the renewal's sale order."""
        self.referrer.commission_plan_id = self.gold_plan

        form = Form(self.env['sale.order'].with_user(self.salesman).with_context(tracking_disable=True),
                    view=self.env.ref('sale_subscription.sale_subscription_primary_form_view'))
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        # form.commission_plan_frozen = False
        form.plan_id = self.plan_month
        with form.order_line.new() as line:
            line.name = self.worker.name
            line.product_id = self.worker
            line.product_uom_qty = 1

        form.end_date = fields.Date.today()
        so = form.save()
        so.action_confirm()
        so.next_invoice_date += relativedelta(months=1) # prevent validation error
        res = so.prepare_renewal_order()
        res_id = res['res_id']
        renewal_so = self.env['sale.order'].browse(res_id)
        renewal_so.order_line.product_uom_qty = 1
        self.assertEqual(renewal_so.referrer_id, so.referrer_id)
        self.assertEqual(renewal_so.commission_plan_id, so.commission_plan_id)

    def test_compute_commission(self):
        self.referrer.commission_plan_id = self.gold_plan

        form = Form(self.env['sale.order'].with_user(self.salesman).with_context(tracking_disable=True))
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        # We test the non recurring flow: recurring_invoice is False on the product
        self.worker.recurring_invoice = False
        with form.order_line.new() as line:
            line.name = self.worker.name
            line.product_id = self.worker
            line.product_uom_qty = 2

        so = form.save()
        so.pricelist_id = self.usd_8
        so.action_confirm()

        self.assertEqual(so.commission, 180)

    def test_commission_plan_assignation(self):
        """
        - When 'fixed' the commission plan set on the susbcription is used regardless of the referrer's commission plan.
        """
        self.referrer.commission_plan_id = self.gold_plan

        # Test that it works even when the commission plan is Falsy.
        form = Form(self.env['sale.order'].with_context(tracking_disable=True), view=self.env.ref('sale_subscription.sale_subscription_primary_form_view'))
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        form.sale_order_template_id = self.template_yearly
        form.pricelist_id = self.usd_8

        with form.order_line.new() as line:
            line.name = self.worker.name
            line.product_id = self.worker
            line.product_uom_qty = 2

        # `commission_plan_frozen` and `end_date` are invisible until `is_subscription` is True
        # `is_subscription` is True when there are recurring lines in the sale order.
        form.commission_plan_frozen = True
        form.commission_plan_id = self.env['commission.plan']

        sub = form.save()
        sub.action_confirm()
        sub._cron_recurring_create_invoice()
        # renew
        res = sub.prepare_renewal_order()
        res_id = res['res_id']
        renewal_so = self.env['sale.order'].browse(res_id)
        renewal_so.order_line.product_uom_qty = 2
        renewal_so.action_confirm()

        # pay
        inv = renewal_so._create_invoices()
        inv.action_post()
        self._pay_invoice(inv)

        self.assertFalse(inv.commission_po_line_id)

        # Switch to the greedy plan and renew again.
        renewal_so.commission_plan_id = self.greedy_plan

        # renew
        res = renewal_so.prepare_renewal_order()
        res_id = res['res_id']
        renewal_so_2 = self.env['sale.order'].browse(res_id)
        renewal_so_2.order_line.product_uom_qty = 1
        renewal_so_2.action_confirm()

        # pay
        inv = renewal_so_2._create_invoices()
        inv.action_post()
        self._pay_invoice(inv)

        self.assertEqual(inv.commission_po_line_id.price_subtotal, 18, 'Commission is wrong')

        # Switch to unfrozen and check that the gold plan is used.
        renewal_so_2.commission_plan_frozen = False
        self.assertEqual(renewal_so_2.commission_plan_id, self.gold_plan)

        # renew
        res = renewal_so_2.prepare_renewal_order()
        res_id = res['res_id']
        renewal_so_3 = self.env['sale.order'].browse(res_id)
        renewal_so_3.order_line.product_uom_qty = 2
        renewal_so_3.action_confirm()

        # pay
        inv = renewal_so_3._create_invoices()
        inv.action_post()
        self._pay_invoice(inv)

        self.assertEqual(inv.commission_po_line_id.price_subtotal, 180, 'Commission is wrong')

    def test_commission_plan_frozen(self):
        """
            Check the change of option `commission_plan_frozen`
            with commission plan and vice versa
        """
        self.referrer.commission_plan_id = self.gold_plan

        # [1.] Save subscription with commission plan frozen enabled
        # --> commission plan can be redefined
        form = Form(self.env['sale.order'])
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        form.sale_order_template_id = self.template_yearly
        # Subscription plan is defined by the product and pricing
        with form.order_line.new() as line:
            line.name = self.worker.name
            line.product_id = self.worker
            line.product_uom_qty = 1
        form.commission_plan_frozen = True
        form.commission_plan_id = self.silver_plan
        sub_A = form.save()
        sub_A.action_confirm()
        sub_A._cron_recurring_create_invoice()
        self.assertEqual(sub_A.commission_plan_id, self.silver_plan)
        self.assertEqual(sub_A.commission_plan_frozen, True)

        # [2.] Save subscription with commission plan frozen disabled
        # --> commission plan cannot be redefined, it will be the referrer commission plan
        form = Form(self.env['sale.order'])
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        form.sale_order_template_id = self.template_yearly
        # Subscription plan is defined by the product and pricing
        with form.order_line.new() as line:
            line.name = self.worker.name
            line.product_id = self.worker
            line.product_uom_qty = 1
        form.commission_plan_frozen = True
        form.commission_plan_id = self.silver_plan
        form.commission_plan_frozen = False
        sub_B = form.save()
        sub_B.action_confirm()
        sub_B._cron_recurring_create_invoice()
        self.assertEqual(sub_B.commission_plan_id, self.gold_plan)
        self.assertEqual(sub_B.commission_plan_frozen, False)

        # [3.] Save subscription with commission plan frozen and default commission plan
        # --> commission plan frozen remains enabled
        form = Form(self.env['sale.order'])
        form.partner_id = self.customer
        form.referrer_id = self.referrer
        form.sale_order_template_id = self.template_yearly
        # Subscription plan is defined by the product and pricing
        with form.order_line.new() as line:
            line.name = self.worker.name
            line.product_id = self.worker
            line.product_uom_qty = 1
        form.commission_plan_frozen = True
        sub_C = form.save()
        sub_C.action_confirm()
        sub_C._cron_recurring_create_invoice()
        self.assertEqual(sub_C.commission_plan_id, self.gold_plan)
        self.assertEqual(sub_C.commission_plan_frozen, True)

        # [4.] Renew subscription with commission plan frozen enabled
        # --> keep the same commission plan
        sub_A_renew_id = sub_A.prepare_renewal_order()['res_id']
        sub_A_renew = self.env['sale.order'].browse(sub_A_renew_id)
        self.assertEqual(sub_A_renew.commission_plan_id, self.silver_plan)

        # [5.] Renew subscription with commission plan frozen disabled
        # --> use referrer's commission plan
        sub_A.commission_plan_frozen = False
        sub_A_renew_id = sub_A.prepare_renewal_order()['res_id']
        sub_A_renew = self.env['sale.order'].browse(sub_A_renew_id)
        self.assertEqual(sub_A_renew.commission_plan_id, self.gold_plan)

        # [6.] Renew subscription with commission plan frozen enabled and default commission plan
        # --> commission plan frozen has to be disabled
        sub_C_renew_id = sub_C.prepare_renewal_order()['res_id']
        sub_C_renew = self.env['sale.order'].browse(sub_C_renew_id)
        self.assertEqual(sub_C_renew.commission_plan_frozen, False)
