# -*- coding: utf-8 -*-

import datetime

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo import Command


class TestSubscriptionCommon(TestSaleCommon):

    def setUp(self):

        super(TestSubscriptionCommon, self).setUp()

        SO = type(self.env['sale.order'])

        def _subscription_launch_cron_single(self, batch_size):
            self.env['sale.order']._create_recurring_invoice(batch_size=batch_size)

        self.patch(SO, '_subscription_launch_cron_parallel', _subscription_launch_cron_single)

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.ref('base.main_company').currency_id = cls.env.ref('base.USD')

        # disable most emails for speed
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}
        AnalyticPlan = cls.env['account.analytic.plan'].with_context(context_no_mail)
        Analytic = cls.env['account.analytic.account'].with_context(context_no_mail)
        SaleOrder = cls.env['sale.order'].with_context(context_no_mail)
        SubPlan = cls.env['sale.subscription.plan'].with_context(context_no_mail)
        SubPricing = cls.env['sale.subscription.pricing'].with_context(context_no_mail)
        Tax = cls.env['account.tax'].with_context(context_no_mail)
        ProductTmpl = cls.env['product.template'].with_context(context_no_mail)
        cls.country_belgium = cls.env.ref('base.be')

        # Minimal CoA & taxes setup
        cls.account_payable = cls.company_data['default_account_payable']
        cls.account_receivable = cls.company_data['default_account_receivable']
        cls.account_income = cls.company_data['default_account_revenue']
        cls.company_data['company'].deferred_journal_id = cls.company_data['default_journal_misc'].id
        cls.company_data['company'].deferred_expense_account_id = cls.company_data['default_account_deferred_expense'].id
        cls.company_data['company'].deferred_revenue_account_id = cls.company_data['default_account_deferred_revenue'].id

        cls.tax_10 = Tax.create({
            'name': "10% tax",
            'amount_type': 'percent',
            'amount': 10,
        })
        cls.tax_20 = Tax.create({
            'name': "20% tax",
            'amount_type': 'percent',
            'amount': 20,
        })
        cls.journal = cls.company_data['default_journal_sale']

        # Test products
        cls.plan_week = SubPlan.create({'name': 'Weekly', 'billing_period_value': 1, 'billing_period_unit': 'week'})
        cls.plan_month = SubPlan.create({'name': 'Monthly', 'billing_period_value': 1, 'billing_period_unit': 'month'})
        cls.plan_year = SubPlan.create({'name': 'Yearly', 'billing_period_value': 1, 'billing_period_unit': 'year'})
        cls.plan_2_month = SubPlan.create({'name': '2 Months', 'billing_period_value': 2, 'billing_period_unit': 'month'})

        cls.pricing_month = SubPricing.create({'plan_id': cls.plan_month.id, 'price': 1})
        cls.pricing_year = SubPricing.create({'plan_id': cls.plan_year.id, 'price': 100})
        cls.pricing_year_2 = SubPricing.create({'plan_id': cls.plan_year.id, 'price': 200})
        cls.pricing_year_3 = SubPricing.create({'plan_id': cls.plan_year.id, 'price': 300})
        cls.sub_product_tmpl = ProductTmpl.create({
            'name': 'BaseTestProduct',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'product_subscription_pricing_ids': [(6, 0, (cls.pricing_month | cls.pricing_year).ids)]
        })
        cls.product = cls.sub_product_tmpl.product_variant_id
        cls.product.write({
            'list_price': 50.0,
            'taxes_id': [(6, 0, [cls.tax_10.id])],
            'property_account_income_id': cls.account_income.id,
        })

        cls.product_tmpl_2 = ProductTmpl.create({
            'name': 'TestProduct2',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
        })
        cls.product2 = cls.product_tmpl_2.product_variant_id
        cls.product2.write({
            'list_price': 20.0,
            'taxes_id': [(6, 0, [cls.tax_10.id])],
            'property_account_income_id': cls.account_income.id,
        })

        cls.product_tmpl_3 = ProductTmpl.create({
            'name': 'TestProduct3',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
        })
        cls.product3 = cls.product_tmpl_3.product_variant_id
        cls.product3.write({
            'list_price': 15.0,
            'taxes_id': [(6, 0, [cls.tax_10.id])],
            'property_account_income_id': cls.account_income.id,
        })

        cls.product_tmpl_4 = ProductTmpl.create({
            'name': 'TestProduct4',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
        })
        cls.product4 = cls.product_tmpl_4.product_variant_id
        cls.product4.write({
            'list_price': 15.0,
            'taxes_id': [(6, 0, [cls.tax_20.id])],
            'property_account_income_id': cls.account_income.id,
        })
        cls.product_tmpl_5 = ProductTmpl.create({
            'name': 'One shot product',
            'type': 'service',
            'recurring_invoice': False,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
        })
        cls.product5 = cls.product_tmpl_3.product_variant_id
        cls.product5.write({
            'list_price': 42.0,
            'taxes_id': [(6, 0, [cls.tax_10.id])],
            'property_account_income_id': cls.account_income.id,
        })
        cls.subscription_tmpl = cls.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'is_unlimited': False,
            'duration_value': 2,
            'duration_unit': 'year',
            'note': "This is the template description",
            'plan_id': cls.plan_month.id,
            'sale_order_template_line_ids': [Command.create({
                'name': "Product 1",
                'product_id': cls.product.id,
                'product_uom_qty': 1,
                'product_uom_id': cls.product.uom_id.id
            }),
                Command.create({
                    'name': "Product 2",
                    'product_id': cls.product2.id,
                    'product_uom_qty': 1,
                    'product_uom_id': cls.product2.uom_id.id,
                })
            ]
        })
        cls.templ_5_days = cls.env['sale.order.template'].create({
            'name': 'Template 2 days',
            'is_unlimited': False,
            'note': "This is the template description",
            'duration_value': 4,
            'duration_unit': 'year',
            'plan_id': cls.plan_year.copy(default={'auto_close_limit': 5}).id,
            'sale_order_template_line_ids': [
                (0, 0, {
                    'name': cls.product.name,
                    'product_id': cls.product.id,
                    'product_uom_qty': 3.0,
                    'product_uom_id': cls.product.uom_id.id,
                }),
                (0, 0, {
                    'name': cls.product2.name,
                    'product_id': cls.product2.id,
                    'product_uom_qty': 2.0,
                    'product_uom_id': cls.product2.uom_id.id,
                })
            ],

        })
        cls.templ_60_days = cls.templ_5_days.copy()
        cls.templ_60_days.plan_id = cls.plan_year.copy(default={'auto_close_limit': 60})

        # Test user
        TestUsersEnv = cls.env['res.users'].with_context({'no_reset_password': True})
        group_portal_id = cls.env.ref('base.group_portal').id
        cls.country_belgium = cls.env.ref('base.be')
        cls.user_portal = TestUsersEnv.create({
            'name': 'Beatrice Portal',
            'login': 'Beatrice',
            'country_id': cls.country_belgium.id,
            'email': 'beatrice.employee@example.com',
            'groups_id': [(6, 0, [group_portal_id])],
            'property_account_payable_id': cls.account_payable.id,
            'property_account_receivable_id': cls.account_receivable.id,
            'company_id': cls.company_data['company'].id,
        })

        cls.malicious_user = TestUsersEnv.create({
            'name': 'Al Capone',
            'login': 'al',
            'password': 'alalalal',
            'email': 'al@capone.it',
            'groups_id': [(6, 0, [group_portal_id])],
            'property_account_receivable_id': cls.account_receivable.id,
            'property_account_payable_id': cls.account_receivable.id,
        })
        cls.legit_user = TestUsersEnv.create({
            'name': 'Eliot Ness',
            'login': 'ness',
            'password': 'nessnessness',
            'email': 'ness@USDT.us',
            'groups_id': [(6, 0, [group_portal_id])],
            'property_account_receivable_id': cls.account_receivable.id,
            'property_account_payable_id': cls.account_receivable.id,
        })

        # Test analytic account
        cls.plan_1 = AnalyticPlan.create({
            'name': 'Test Plan 1',
        })
        cls.account_1 = Analytic.create({
            'partner_id': cls.user_portal.partner_id.id,
            'name': 'Test Account 1',
            'plan_id': cls.plan_1.id,
        })
        cls.account_2 = Analytic.create({
            'partner_id': cls.user_portal.partner_id.id,
            'name': 'Test Account 2',
            'plan_id': cls.plan_1.id,
        })

        # Test Subscription
        cls.subscription = SaleOrder.create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'plan_id': cls.plan_month.id,
            'note': "original subscription description",
            'partner_id': cls.user_portal.partner_id.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'sale_order_template_id': cls.subscription_tmpl.id,
        })
        cls.subscription._onchange_sale_order_template_id()
        cls.subscription.start_date = False # the confirmation will set the start_date
        cls.subscription.end_date = False # reset the end_date too
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref('base.us')
        cls.account_receivable = cls.env['account.account'].create(
            {'name': 'Ian Anderson',
             'code': 'IA',
             'account_type': 'asset_receivable',
             'company_id': cls.company.id,
             'reconcile': True})
        cls.account_sale = cls.env['account.account'].create(
            {'name': 'Product Sales ',
             'code': 'S200000',
             'account_type': 'income',
             'company_id': cls.company.id,
             'reconcile': False})

        cls.sale_journal = cls.env['account.journal'].create(
            {'name': 'reflets.info',
             'code': 'ref',
             'type': 'sale',
             'company_id': cls.company.id,
             'default_account_id': cls.account_sale.id})
        belgium = cls.env.ref('base.be')
        cls.partner = cls.env['res.partner'].create(
            {'name': 'Stevie Nicks',
             'email': 'sti@fleetwood.mac',
             'country_id': belgium.id,
             'property_account_receivable_id': cls.account_receivable.id,
             'property_account_payable_id': cls.account_receivable.id,
             'company_id': cls.company.id})
        cls.provider = cls.env['payment.provider'].create(
            {'name': 'The Wire',
             'company_id': cls.company.id,
             'state': 'test',
             'redirect_form_view_id': cls.env['ir.ui.view'].search([('type', '=', 'qweb')], limit=1).id})
        cls.payment_method_id = cls.env.ref('payment.payment_method_unknown').id
        cls.payment_token = cls.env['payment.token'].create(
            {'payment_details': 'Jimmy McNulty',
             'partner_id': cls.partner.id,
             'provider_id': cls.provider.id,
             'payment_method_id': cls.payment_method_id,
             'provider_ref': 'Omar Little'})
        Partner = cls.env['res.partner']
        cls.partner_a_invoice = Partner.create({
            'parent_id': cls.partner_a.id,
            'type': 'invoice',
        })
        cls.partner_a_shipping = Partner.create({
            'parent_id': cls.partner_a.id,
            'type': 'delivery',
        })
        cls.mock_send_success_count = 0

    # Mocking for 'test_auto_payment_with_token'
    # Necessary to have a valid and done transaction when the cron on subscription passes through
    def _mock_subscription_do_payment(self, payment_token, invoice, auto_commit=False):
        tx_obj = self.env['payment.transaction']
        refs = invoice.invoice_line_ids.sale_line_ids.order_id.mapped('client_order_ref')
        ref_vals = [r for r in refs if r]
        reference = "CONTRACT-%s-%s-%s" % (invoice.id,
                                           ''.join(ref_vals),
                                           datetime.datetime.now().strftime('%y%m%d_%H%M%S%f'))
        provider = invoice.env.context.get('test_provider', self.provider)
        values = [{
            'amount': invoice.amount_total,
            'provider_id': provider.id,
            'payment_method_id': self.payment_method_id,
            'operation': 'offline',
            'currency_id': invoice.currency_id.id,
            'reference': reference,
            'token_id': payment_token.id,
            'partner_id': invoice.partner_id.id,
            'partner_country_id': invoice.partner_id.country_id.id,
            'sale_order_ids': [(6, 0, invoice.invoice_line_ids.sale_line_ids.order_id.ids)],
            'invoice_ids': [(6, 0, [invoice.id])],
            'state': 'done',
            'subscription_action': 'automatic_send_mail',
        }]
        tx = tx_obj.create(values)
        return tx

    def _mock_subscription_do_payment_rejected(self, payment_method, invoice, auto_commit=False):
        tx = self._mock_subscription_do_payment(payment_method, invoice)
        tx.state = "pending"
        tx._set_error("Payment declined")
        tx.env.cr.flush()  # simulate commit after sucessfull `_do_payment()`
        return tx

    # Mocking for 'test_auto_payment_with_token'
    # Otherwise the whole sending mail process will be triggered
    # And we are not here to test that flow, and it is a heavy one
    def _mock_subscription_send_success_mail(self, tx, invoice):
        self.mock_send_success_count += 1
        return 666

    # Mocking for 'test_auto_payment_with_token'
    # Avoid account_id is False when creating the invoice
    def _mock_prepare_invoice_data(self):
        invoice = self.original_prepare_invoice()
        invoice['partner_bank_id'] = False
        return invoice

    def flush_tracking(self):
        self.env.flush_all()
        self.cr.flush()
