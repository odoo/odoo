# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo.tests import tagged
from odoo import fields, Command

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('-at_install', 'post_install')
class TestSaleSubscriptionProjectProfitability(TestProjectProfitabilityCommon, TestSubscriptionCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

        cls.project.write({
            'partner_id': cls.user_portal.partner_id.id,
            'company_id': False,
            'account_id': cls.account_1.id,
        })

        cls.product_no_tax = cls.sub_product_tmpl.product_variant_id
        cls.subscription_tmpl_foreign_company = cls.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'note': "This is the template description",
            'plan_id': cls.plan_month.id,
            'company_id': False,
            'sale_order_template_line_ids': [Command.create({
                'name': "Product 1",
                'product_id': cls.product_no_tax.id,
                'product_uom_qty': 1,
                'product_uom_id': cls.product_no_tax.uom_id.id,
            }), Command.create({
                    'name': "Product 2",
                    'product_id': cls.product_no_tax.id,
                    'product_uom_qty': 2,
                    'product_uom_id': cls.product_no_tax.uom_id.id,
            })]
        })

        cls.subscription_foreign, cls.subscription_main_with_foreign_template = cls.env['sale.order'].create([{
            'name': 'TestSubscription',
            'is_subscription': True,
            'plan_id': cls.plan_month.id,
            'note': "original subscription description",
            'partner_id': cls.user_portal.partner_id.id,
            'pricelist_id': cls.company_data_2['default_pricelist'].id,
            'company_id': cls.company_data_2['company'].id,
            'sale_order_template_id': cls.subscription_tmpl_foreign_company.id,
        }, {
            'name': 'TestSubscription',
            'is_subscription': True,
            'plan_id': cls.plan_month.id,
            'note': "original subscription description",
            'partner_id': cls.user_portal.partner_id.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'company_id': cls.company_data['company'].id,
            'sale_order_template_id': cls.subscription_tmpl_foreign_company.id,
        }])
        cls.subscription_foreign._onchange_sale_order_template_id()
        cls.subscription_main_with_foreign_template._onchange_sale_order_template_id()

    def test_project_profitability(self):
        self.project.company_id = False
        project_vals = {'project_id': self.project.id}

        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency

        # Create and confirm a subscription with the foreign company
        subscription_foreign = self.subscription_foreign.copy(project_vals)
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the subscription is still in draft.'
        )
        subscription_foreign.currency_id = self.foreign_currency
        subscription_foreign.order_line.price_unit = 100
        subscription_foreign.action_confirm()

        self.assertEqual(subscription_foreign.subscription_state, '3_progress')
        self.assertEqual(len(subscription_foreign.order_line), 2)
        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('subscriptions', sequence_per_invoice_type)
        subscription_sequence = sequence_per_invoice_type['subscriptions']
        new_amount_expected = subscription_foreign.recurring_monthly * subscription_foreign.sale_order_template_id.duration_value * 0.2
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions', 'sequence': subscription_sequence, 'to_invoice': new_amount_expected, 'invoiced': 0.0,
                    }],
                    'total': {'to_invoice': new_amount_expected, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [],
                    'total': {'to_bill': 0.0, 'billed': 0.0},
                }
            }
        )

        # Create and confirm a subscription with the main company and the same template as the foreign subscription
        # This ensures that even if subscriptions share a template, the currency is correctly computed
        subscription_main_with_foreign_template = self.subscription_main_with_foreign_template.copy(project_vals)
        subscription_main_with_foreign_template.order_line.price_unit = 100
        subscription_main_with_foreign_template.action_confirm()
        new_amount_expected += subscription_main_with_foreign_template.recurring_monthly * subscription_main_with_foreign_template.sale_order_template_id.duration_value
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions', 'sequence': subscription_sequence, 'to_invoice': new_amount_expected, 'invoiced': 0.0,
                    }],
                    'total': {'to_invoice': new_amount_expected, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [],
                    'total': {'to_bill': 0.0, 'billed': 0.0},
                }
            }
        )
        # Confirm the main company subscription
        # This ensures that subscriptions with different template are correctly computed
        subscription = self.subscription.copy(project_vals)
        subscription.action_confirm()
        new_amount_expected += subscription.recurring_monthly * subscription.sale_order_template_id.duration_value
        # There are more than 5 sale lines, the allSubscriptionIds arg is now expected
        all_ids = subscription.order_line.ids
        all_ids.extend(subscription_main_with_foreign_template.order_line.ids)
        all_ids.extend(subscription_foreign.order_line.ids)
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions', 'sequence': subscription_sequence, 'to_invoice': new_amount_expected, 'invoiced': 0.0,
                    }],
                    'total': {'to_invoice': new_amount_expected, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [],
                    'total': {'to_bill': 0.0, 'billed': 0.0},
                }
            }
        )

    def test_project_profitability_with_subscription_without_template(self):
        project_vals = {'sale_order_template_id': False, 'project_id': self.project.id}
        self.project.company_id = False

        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency

        # Create and confirm a subscription with the foreign company
        subscription_foreign = self.subscription_foreign.copy(project_vals)
        subscription_foreign.project_id = self.project
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the subscription is still in draft.'
        )
        subscription_foreign.currency_id = self.foreign_currency
        subscription_foreign.order_line.price_unit = 100
        subscription_foreign.action_confirm()
        self.assertEqual(subscription_foreign.subscription_state, '3_progress')
        self.assertEqual(len(subscription_foreign.order_line), 2)
        self.assertFalse(subscription_foreign.sale_order_template_id, 'No template should be set in this subscription.')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions',
                        'sequence': self.project._get_profitability_sequence_per_invoice_type()['subscriptions'],
                        'to_invoice': subscription_foreign.recurring_monthly * 0.2,
                        'invoiced': 0.0,
                    }],
                    'total': {'to_invoice': subscription_foreign.recurring_monthly * 0.2, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [],
                    'total': {'to_bill': 0.0, 'billed': 0.0},
                }
            }
        )

        # Confirm the main company subscription
        # This ensures that subscriptions with different template are correctly computed
        subscription = self.subscription.copy(project_vals)
        subscription.action_confirm()
        self.assertEqual(subscription.subscription_state, '3_progress')
        self.assertEqual(len(subscription.order_line), 2)
        self.assertFalse(subscription.sale_order_template_id, 'No template should be set in this subscription.')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions',
                        'sequence': self.project._get_profitability_sequence_per_invoice_type()['subscriptions'],
                        'to_invoice': subscription_foreign.recurring_monthly * 0.2 + subscription.recurring_monthly,
                        'invoiced': 0.0,
                    }],
                    'total': {'to_invoice': subscription_foreign.recurring_monthly * 0.2 + subscription.recurring_monthly, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [],
                    'total': {'to_bill': 0.0, 'billed': 0.0},
                }
            }
        )

    def test_recurrent_fixed_service_only_in_subscription_section(self):
        """
        A recurrent service with prepaid/fixed invoicing should only be included in
        the subscription section, not the "Fixed Hourly" cost. (because it is recurrent)
        """
        self.project.company_id = False

        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency
        self.project.allow_billable = True
        product_service_fixed_recurrent = self.product_no_tax
        product_service_fixed_recurrent.write({
            'name': "Recurrent Service with Prepaid/Fixed Invoicing Policy",
            'service_policy': 'ordered_prepaid',
            'service_tracking': 'task_global_project',
            'project_id': self.project.id,
        })
        sale_order_foreign = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'project_id': self.project.id,
            'company_id': foreign_company.id,
        })
        self.env['sale.order.line'].with_context(tracking_disable=True).create({
            'product_id': product_service_fixed_recurrent.id,
            'product_uom_qty': 10,
            'order_id': sale_order_foreign.id,
        })
        sale_order_foreign.currency_id = self.foreign_currency
        sale_order_foreign.action_confirm()
        # there should be only a subscription section, not the fixed/prepaid services section
        self.assertDictEqual(
            self.project._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'subscriptions',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['subscriptions'],
                    'to_invoice': sale_order_foreign.recurring_monthly * 0.2,
                    'invoiced': 0.0,
                }],
                'total': {'to_invoice': sale_order_foreign.recurring_monthly * 0.2, 'invoiced': 0.0},
            },
        )

        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'project_id': self.project.id,
        })
        self.env['sale.order.line'].with_context(tracking_disable=True).create({
            'product_id': product_service_fixed_recurrent.id,
            'product_uom_qty': 10,
            'order_id': sale_order.id,
        })
        sale_order.action_confirm()
        # there should be only a subscription section, not the fixed/prepaid services section
        self.assertDictEqual(
            self.project._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'subscriptions',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['subscriptions'],
                    'to_invoice': sale_order.recurring_monthly + sale_order_foreign.recurring_monthly * 0.2,
                    'invoiced': 0.0,
                }],
                'total': {'to_invoice': sale_order.recurring_monthly + sale_order_foreign.recurring_monthly * 0.2, 'invoiced': 0.0},
            },
        )

    def test_project_update(self):
        """Test that the project update panel works when the project
        is linked to a closed subscription that was invoiced."""
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        sale_order = self.env['sale.order'].create({
            'is_subscription': True,
            'note': "original subscription description",
            'partner_id': self.partner.id,
            'project_id': self.project.id,
            'plan_id': self.plan_month.id,
            'end_date': fields.Date.today() + relativedelta(months=1),
        })
        product = self.env['product.template'].create([{
            'name': 'Test Product',
            'recurring_invoice': True,
            'type': 'service',
            'project_id': self.project.id,
            'service_tracking': 'task_global_project',
        }])
        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': product.product_variant_id.id,
        })
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()
        self.env['account.analytic.line'].create([{
            'name': 'Sale',
            'move_line_id': invoice.line_ids[0].id,
            'account_id': self.project.account_id.id,
            'currency_id': self.company_data['currency'].id,
            'amount': 1,
        }])
        sale_order.set_close()
        self.assertDictEqual(
            self.project._get_profitability_items(with_action=False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions',
                        'sequence': 8,
                        'invoiced': 1.0,
                        'to_invoice': 0.0,
                    }],
                    'total': {'invoiced': 1.0, 'to_invoice': 0.0},
                },
                'costs': {
                    'data': [],
                    'total': {'billed': 0.0, 'to_bill': 0.0}
                }
            }
        )

    def test_project_profitability_with_renewed_subscription(self):
        """
        Test that the project profitability is correctly updated when a subscription is renewed.

        Test Case:
        ==========
        1- create a subscription and link it to a project
        2- confirm the subscription and create an invoice and post it
        3- renew the subscription
        4- check that `To Invoice` reflects the new subscription amount while `Invoiced` takes
           into account previous subscription.
        """
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        subscription = self.env['sale.order'].create({
            'is_subscription': True,
            'note': "original subscription description",
            'partner_id': self.partner.id,
            'project_id': self.project.id,
            'plan_id': self.plan_month.id,
            'end_date': fields.Date.today() + relativedelta(months=1),
        })
        product = self.env['product.template'].create([{
            'name': 'Test Product',
            'recurring_invoice': True,
            'type': 'service',
        }])
        self.env['sale.order.line'].create({
            'order_id': subscription.id,
            'product_id': product.product_variant_id.id,
            'price_unit': 100,
        })
        subscription.action_confirm()
        invoice = subscription._create_invoices()
        invoice.action_post()
        self.env['account.analytic.line'].create([{
            'name': 'Sale',
            'move_line_id': invoice.line_ids[0].id,
            'account_id': self.project.account_id.id,
            'currency_id': self.company_data['currency'].id,
            'amount': 100.0,
        }])

        self.assertDictEqual(
            self.project._get_profitability_items(with_action=False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions',
                        'sequence': 8,
                        'invoiced': 100.0,
                        'to_invoice': 100.0
                    }],
                    'total': {'invoiced': 100.0, 'to_invoice': 100.0},
                },
                'costs': {
                    'data': [],
                    'total': {'billed': 0.0, 'to_bill': 0.0}
                }
            }
        )

        # Renew the subscription
        action = subscription.prepare_renewal_order()
        renewed_sub = self.env['sale.order'].browse(action['res_id'])
        renewed_sub.action_confirm()
        renewed_invoice = renewed_sub._create_invoices()
        renewed_invoice.action_post()
        self.env['account.analytic.line'].create([{
            'name': 'Sale',
            'move_line_id': invoice.line_ids[0].id,
            'account_id': self.project.account_id.id,
            'currency_id': self.company_data['currency'].id,
            'amount': 100.0,
        }])

        self.assertDictEqual(
            self.project._get_profitability_items(with_action=False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions',
                        'sequence': 8,
                        'invoiced': 200.0,
                        'to_invoice': 100.0,
                    }],
                    'total': {'invoiced': 200.0, 'to_invoice': 100.0},
                },
                'costs': {
                    'data': [],
                    'total': {'billed': 0.0, 'to_bill': 0.0}
                }
            }
        )
