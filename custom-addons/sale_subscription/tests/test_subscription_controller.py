# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from datetime import date
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.tests.common import new_test_user, tagged
from odoo.tools import mute_logger
from odoo import Command
from odoo import http


@tagged("post_install", "-at_install", "subscription_controller")
class TestSubscriptionController(PaymentHttpCommon, PaymentCommon, TestSubscriptionCommon):
    def setUp(self):
        super().setUp()
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True,}
        SaleOrder = self.env['sale.order'].with_context(context_no_mail)
        ProductTmpl = self.env['product.template'].with_context(context_no_mail)

        self.user = new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", tz="UTC")
        self.other_user = new_test_user(self.env, "test_user_2", email="test_user_2@nowhere.com", password="P@ssw0rd!", tz="UTC")

        self.partner = self.user.partner_id
        # Test products
        self.sub_product_tmpl = ProductTmpl.sudo().create({
            'name': 'TestProduct',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'product_subscription_pricing_ids': [Command.set((self.pricing_month + self.pricing_year).ids)],
        })
        self.subscription_tmpl = self.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'duration_unit': 'year',
            'is_unlimited': False,
            'duration_value': 2,
            'note': "This is the template description",
            'plan_id': self.plan_month.id,
            'sale_order_template_line_ids': [Command.create({
                'name': "monthly",
                'product_id': self.sub_product_tmpl.product_variant_ids.id,
                'product_uom_qty': 1,
                'product_uom_id': self.sub_product_tmpl.uom_id.id
            }),
                Command.create({
                    'name': "yearly",
                    'product_id': self.sub_product_tmpl.product_variant_ids.id,
                    'product_uom_qty': 1,
                    'product_uom_id': self.sub_product_tmpl.uom_id.id,
                })
            ]

        })
        # Test Subscription
        self.subscription = SaleOrder.create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'note': "original subscription description",
            'partner_id': self.other_user.partner_id.id,
            'pricelist_id':  self.other_user.property_product_pricelist.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        self.subscription._onchange_sale_order_template_id()
        self.subscription.end_date = False  # reset the end_date
        self.subscription_tmpl.flush_recordset()
        self.subscription.flush_recordset()

    def test_close_contract(self):
        """ Test subscription close """
        with freeze_time("2021-11-18"):
            self.authenticate(None, None)
            self.subscription.plan_id.user_closable = True
            self.subscription.action_confirm()
            close_reason_id = self.env.ref('sale_subscription.close_reason_1')
            data = {'access_token': self.subscription.access_token, 'csrf_token': http.Request.csrf_token(self),
                    'close_reason_id': close_reason_id.id, 'closing_text': "I am broke"}
            url = "/my/subscriptions/%s/close" % self.subscription.id
            res = self.url_open(url, allow_redirects=False, data=data)
            self.assertEqual(res.status_code, 303)
            self.env.invalidate_all()
            self.assertEqual(self.subscription.subscription_state, '6_churn', 'The subscription should be closed.')
            self.assertEqual(self.subscription.end_date, date(2021, 11, 18), 'The end date of the subscription should be updated.')

    def test_prevents_assigning_not_owned_payment_tokens_to_subscriptions(self):
        malicious_user_subscription = self.env['sale.order'].create({
            'name': 'Free Subscription',
            'partner_id': self.malicious_user.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        malicious_user_subscription._onchange_sale_order_template_id()

        legit_user_subscription = self.env['sale.order'].create({
            'name': 'Free Subscription',
            'partner_id': self.legit_user.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        stolen_payment_method = self.env['payment.token'].create(
            {'payment_details': 'Jimmy McNulty',
             'partner_id': self.malicious_user.partner_id.id,
             'provider_id': self.dummy_provider.id,
             'payment_method_id': self.payment_method_id,
             'provider_ref': 'Omar Little'})
        legit_payment_method = self.env['payment.token'].create(
            {'payment_details': 'Jimmy McNulty',
             'partner_id': self.legit_user.partner_id.id,
             'provider_id': self.dummy_provider.id,
             'payment_method_id': self.payment_method_id,
             'provider_ref': 'Legit ref'})
        legit_user_subscription._portal_ensure_token()
        malicious_user_subscription._portal_ensure_token()
        # Payment Token exists/does not exists
        # Payment Token is accessible to user/not accessible
        # SO accessible to User/Accessible thanks to the token/Not Accessible (wrong token, no token)
        # First we check a legit token assignation for a legit subscription.
        self.authenticate('ness', 'nessnessness')
        data = {'token_id': legit_payment_method.id,
                'order_id': legit_user_subscription.id,
                'access_token': legit_user_subscription.access_token
                }
        url = self._build_url("/my/subscriptions/assign_token/%s" % legit_user_subscription.id)
        self.make_jsonrpc_request(url, data)
        legit_user_subscription.invalidate_recordset()
        self.assertEqual(legit_user_subscription.payment_token_id, legit_payment_method)
        data = {'token_id': 9999999999999999, 'order_id': legit_user_subscription.id}
        with self._assertNotFound():
            self.make_jsonrpc_request(url, data)
        legit_user_subscription.invalidate_recordset()
        self.assertEqual(legit_user_subscription.payment_token_id, legit_payment_method, "The new token should be saved on the order.")

        # Payment token is inacessible to user but the SO is OK
        self.authenticate('al', 'alalalal')
        data = {'token_id': legit_payment_method.id, 'order_id': malicious_user_subscription.id}
        url = self._build_url("/my/subscriptions/assign_token/%s" % malicious_user_subscription.id)
        with self._assertNotFound():
            self.make_jsonrpc_request(url, data)
        malicious_user_subscription.invalidate_recordset()
        self.assertFalse(malicious_user_subscription.payment_token_id, "No token should be saved on the order.")

        # The SO is not accessible but the token is mine
        data = {'token_id': stolen_payment_method.id, 'order_id': legit_user_subscription.id}
        self._build_url("/my/subscriptions/assign_token/%s" % legit_user_subscription.id)
        with self._assertNotFound():
            self.make_jsonrpc_request(url, data)
        legit_user_subscription.invalidate_recordset()
        self.assertEqual(legit_user_subscription.payment_token_id, legit_payment_method, "The token should not be updated")

    def test_automatic_invoice_token(self):

        self.original_prepare_invoice = self.subscription._prepare_invoice
        self.mock_send_success_count = 0
        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment),\
            patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._send_success_mail', wraps=self._mock_subscription_send_success_mail):
            self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'False')
            subscription = self._portal_payment_controller_flow()
            subscription.transaction_ids.unlink()
            # set automatic invoice and restart
            self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
            self._portal_payment_controller_flow()

    def _portal_payment_controller_flow(self):
        subscription = self.subscription.create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'payment_token_id': self.payment_token.id,
            'sale_order_template_id': self.subscription_tmpl.id,

        })
        subscription._onchange_sale_order_template_id()
        subscription.state = 'sent'
        subscription._portal_ensure_token()
        signature = "R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="  # BASE64 of a simple image
        data = {'order_id': subscription.id, 'access_token': subscription.access_token, 'signature': signature}

        url = self._build_url("/my/orders/%s/accept" % subscription.id)
        self.make_jsonrpc_request(url, data)
        data = {
            'provider_id': self.dummy_provider.id,
            'payment_method_id': self.payment_method_id,
            'token_id': None,
            'order_id': subscription.id,
            'access_token': subscription.access_token,
            'amount': subscription.amount_total,
            'flow': 'direct',
            'tokenization_requested': True,
            'landing_route': subscription.get_portal_url(),
        }
        url = self._build_url("/my/orders/%s/transaction" % subscription.id)
        self.make_jsonrpc_request(url, data)
        subscription.transaction_ids.provider_id.support_manual_capture = 'full_only'
        subscription.transaction_ids._set_authorized()
        subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
        subscription.transaction_ids.token_id = self.payment_token.id
        self.assertEqual(subscription.next_invoice_date, datetime.date.today())
        self.assertEqual(subscription.state, 'sale')
        subscription.transaction_ids._reconcile_after_done()  # Create the payment
        self.assertEqual(subscription.invoice_count, 1, "One invoice should be created")
        # subscription has a payment_token_id, the invoice is created by the flow.
        subscription.invoice_ids.invoice_line_ids.account_id.account_type = 'income'
        subscription.invoice_ids.auto_post = 'at_date'
        self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        self.assertTrue(subscription.next_invoice_date > datetime.date.today(), "the next invoice date should be updated")
        self.env['account.payment.register'] \
            .with_context(active_model='account.move', active_ids=subscription.invoice_ids.ids) \
            .create({
            'currency_id': subscription.currency_id.id,
            'amount': subscription.amount_total,
        })._create_payments()
        self.assertEqual(subscription.invoice_ids.mapped('state'), ['posted'])
        self.assertTrue(subscription.invoice_ids.payment_state in ['paid', 'in_payment'])
        subscription._cron_recurring_create_invoice()
        invoices = subscription.invoice_ids.filtered(lambda am: am.state in ['draft', 'posted']) # avoid counting canceled invoices
        self.assertEqual(len(invoices), 1, "Only one invoice should be created")
        # test transaction flow when paying from the portal
        self.assertEqual(len(subscription.transaction_ids), 1, "Only one transaction should be created")
        first_transaction_id = subscription.transaction_ids
        url = self._build_url("/my/subscriptions/%s/transaction" % subscription.id)
        data = {'access_token': subscription.access_token,
                'landing_route': subscription.get_portal_url(),
                'provider_id': self.dummy_provider.id,
                'payment_method_id': self.payment_method_id,
                'token_id': False,
                'flow': 'direct',
                }
        self.make_jsonrpc_request(url, data)
        # the transaction is associated to the invoice in tx._reconcile_after_done()
        invoice_transactions = subscription.invoice_ids.transaction_ids
        self.assertEqual(len(invoice_transactions), 2, "Two transactions should be created. Calling /my/subscriptions/transaction/ creates a new one")
        last_transaction_id = subscription.transaction_ids - first_transaction_id
        self.assertEqual(len(subscription.transaction_ids), 2)
        self.assertEqual(last_transaction_id.sale_order_ids, subscription)
        last_transaction_id._set_done()
        self.assertEqual(subscription.invoice_ids.sorted('id').mapped('state'), ['posted', 'draft'])
        subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
        subscription.transaction_ids._reconcile_after_done()  # Create the payment
        # subscription has a payment_token_id, the invoice is created by the flow.
        subscription.invoice_ids.invoice_line_ids.account_id.account_type = 'asset_cash'
        subscription.invoice_ids.auto_post = 'at_date'
        subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
        self.env['account.payment.register'] \
            .with_context(active_model='account.move', active_ids=subscription.invoice_ids.ids) \
            .create({
            'currency_id': subscription.currency_id.id,
            'amount': subscription.amount_total,
        })._create_payments()
        self.assertFalse(set(subscription.invoice_ids.mapped('payment_state')) & {'not_paid', 'partial'},
                         "All invoices should be in paid or in_payment status")
        return subscription

    def test_controller_transaction_refund(self):
        self.original_prepare_invoice = self.subscription._prepare_invoice
        self.mock_send_success_count = 0
        self.pricing_month.price = 10
        subscription = self.subscription.create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'payment_token_id': self.payment_token.id,
            'sale_order_template_id': self.subscription_tmpl.id,

        })
        subscription._onchange_sale_order_template_id()
        subscription.order_line.product_uom_qty = 2
        subscription.action_confirm()
        invoice = subscription._create_invoices()
        invoice._post()
        self.assertEqual(invoice.amount_total, 46)
        # partial refund
        refund_wizard = self.env['account.move.reversal'].with_context(
            active_model="account.move",
            active_ids=invoice.ids).create({
            'reason': 'Test refund',
            'journal_id': invoice.journal_id.id,
        })
        res = refund_wizard.reverse_moves()
        refund_move = self.env['account.move'].browse(res['res_id'])
        refund_move.invoice_line_ids.quantity = 1
        refund_move._post()
        self.assertEqual(refund_move.amount_total, 23, "The refund is half the invoice")

        url = self._build_url("/my/subscriptions/%s/transaction/" % subscription.id)
        data = {'access_token': subscription.access_token,
                'landing_route': subscription.get_portal_url(),
                'provider_id': self.dummy_provider.id,
                'payment_method_id': self.payment_method_id,
                'token_id': False,
                'flow': 'direct',
                }
        self.make_jsonrpc_request(url, data)
        invoice_transactions = subscription.invoice_ids.transaction_ids
        # the amount should be equal to the last
        self.assertEqual(invoice_transactions.amount, subscription.amount_total,
                         "The last transaction should be equal to the total")

    def test_portal_partial_payment(self):
        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment',
                   wraps=self._mock_subscription_do_payment), \
                patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._send_success_mail',
                      wraps=self._mock_subscription_send_success_mail):
            self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'False')
            with freeze_time("2024-01-22"):
                subscription = self.subscription.create({
                    'partner_id': self.partner.id,
                    'company_id': self.company.id,
                    'sale_order_template_id': self.subscription_tmpl.id,
                })
                self.pricing_month.price = 100
                subscription._onchange_sale_order_template_id()
                subscription.state = 'sent'
                subscription._portal_ensure_token()
                # test customized /payment/pay route with sale_order_id param
                # partial amount specified
                self.amount = subscription.amount_total / 2.0 # self.amount is used to create the right transaction
                pay_route_values = self._prepare_pay_values(
                    amount=self.amount,
                    currency=subscription.currency_id,
                    partner=subscription.partner_id,
                )
                pay_route_values['sale_order_id'] = subscription.id
                tx_context = self._get_portal_pay_context(**pay_route_values)

                tx_route_values = {
                    'provider_id': self.provider.id,
                    'payment_method_id': self.payment_method_id,
                    'token_id': None,
                    'amount': tx_context['amount'],
                    'flow': 'direct',
                    'tokenization_requested': False,
                    'landing_route': '/my/subscriptions',
                    'access_token': tx_context['access_token'],
                }
                with mute_logger('odoo.addons.payment.models.payment_transaction'):
                    processing_values = self._get_processing_values(
                        tx_route=tx_context['transaction_route'], **tx_route_values
                    )
                tx_sudo = self._get_tx(processing_values['reference'])
                # make sure to have a token on the transaction. it is needed to test the confirmation flow
                tx_sudo.token_id = self.payment_token.id
                self.assertEqual(tx_sudo.sale_order_ids, subscription)
                # self.assertEqual(tx_sudo.amount, amount)
                self.assertEqual(tx_sudo.sale_order_ids.transaction_ids, tx_sudo)

                tx_sudo._set_done()
                with mute_logger('odoo.addons.sale.models.payment_transaction'):
                    tx_sudo._finalize_post_processing()
                self.assertEqual(subscription.state, 'sent')  # Only a partial amount was paid
                subscription.action_confirm()
                self.assertEqual(subscription.next_invoice_date, datetime.date.today())
                self.assertEqual(subscription.state, 'sale')
                self.assertEqual(subscription.invoice_count, 0, "No invoice should be created")
                self.assertFalse(subscription.payment_token_id, "No token should be saved")

                # Renew subscription and set payment amount as half of the total amount (partial).
                subscription._create_recurring_invoice()
                action = subscription.prepare_renewal_order()
                renewal_so = self.env['sale.order'].browse(action['res_id'])
                self.amount = renewal_so.amount_total / 2.0

                # Prepare renewal subscription's payment values.
                pay_route_values = self._prepare_pay_values(
                    amount=self.amount,
                    currency=renewal_so.currency_id,
                    partner=renewal_so.partner_id,
                )
                pay_route_values['sale_order_id'] = renewal_so.id
                tx_context = self._get_portal_pay_context(**pay_route_values)

                tx_route_values = {
                    'provider_id': self.provider.id,
                    'payment_method_id': self.payment_method_id,
                    'token_id': None,
                    'amount': tx_context['amount'],
                    'flow': 'direct',
                    'tokenization_requested': False,
                    'landing_route': '/my/subscriptions',
                    'access_token': tx_context['access_token'],
                }
                with mute_logger('odoo.addons.payment.models.payment_transaction'):
                    processing_values = self._get_processing_values(tx_route=tx_context['transaction_route'], **tx_route_values)

                # Make sure to have a token on the transaction, it is needed to test the confirmation flow.
                tx_sudo = self._get_tx(processing_values['reference'])
                tx_sudo.token_id = self.payment_token.id
                self.assertEqual(tx_sudo.sale_order_ids, renewal_so)
                self.assertEqual(tx_sudo.sale_order_ids.transaction_ids, tx_sudo)
                tx_sudo._set_done()
                with mute_logger('odoo.addons.sale.models.payment_transaction'):
                    tx_sudo._finalize_post_processing()

                # Confirm renewal. Assert that no token was saved, renewal was sent and only one invoice was registered.
                renewal_so.action_confirm()
                self.assertFalse(renewal_so.payment_token_id, "No token should be saved")
                self.assertEqual(renewal_so.state, 'sale')
                self.assertEqual(renewal_so.invoice_count, 1, "Only one invoice from previous subscription should be registered")
                self.assertEqual(renewal_so.next_invoice_date, datetime.date.today() + datetime.timedelta(days=31))

    def test_portal_quote_document(self):
        product_document = self.env['product.document'].create({
            'name': 'doc.txt',
            'active': True,
            'datas': 'TXkgYXR0YWNobWVudA==',
            'res_model': 'product.product',
            'res_id': self.sub_product_tmpl.product_variant_ids.id,
            'attached_on': 'sale_order',
        })
        self.subscription.action_confirm()
        response = self.url_open(
            self.subscription.get_portal_url('/document/' + str(product_document.id))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual("My attachment", response.text)
