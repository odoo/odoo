# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch
from freezegun import freeze_time


from odoo import fields, Command
from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestSubscriptionPayments(PaymentCommon, TestSubscriptionCommon, MockEmail):

    def test_auto_payment_with_token(self):

        self.original_prepare_invoice = self.subscription._prepare_invoice

        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment),\
            patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._send_success_mail',
                  wraps=self._mock_subscription_send_success_mail):

            self.subscription.write({
                'partner_id': self.partner.id,
                'company_id': self.company.id,
                'payment_token_id': self.payment_token.id,
                'sale_order_template_id': self.subscription_tmpl.id,
            })
            self.subscription._onchange_sale_order_template_id()
            self.subscription.action_confirm()
            self.mock_send_success_count = 0
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription.transaction_ids._reconcile_after_done()
            self.assertEqual(self.mock_send_success_count, 1, 'a mail to the invoice recipient should have been sent')
            self.assertEqual(self.subscription.subscription_state, '3_progress', 'subscription with online payment and a payment method set should stay opened when transaction succeeds')
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            recurring_total_with_taxes = self.subscription.amount_total
            self.assertEqual(invoice.amount_total, recurring_total_with_taxes,
                             'website_subscription: the total of the recurring invoice created should be the subscription '
                             'recurring total + the products taxes')
            self.assertTrue(all(line.tax_ids.ids == self.tax_10.ids for line in invoice.invoice_line_ids),
                            'website_subscription: All lines of the recurring invoice created should have the percent tax '
                            'set on the subscription products')
            self.assertTrue(
                all(tax_line.tax_line_id == self.tax_10 for tax_line in invoice.line_ids.filtered('tax_line_id')),
                'The invoice tax lines should be set and should all use the tax set on the subscription products')

            self.mock_send_success_count = 0
            start_date = fields.Date.today() - relativedelta(months=1)
            recurring_next_date = fields.Date.today() - relativedelta(days=1)
            self.subscription.payment_token_id = False
            failing_subs = self.env['sale.order']
            subscription_mail_fail = self.subscription.copy({
                'date_order': start_date,
                'start_date': start_date,
                'next_invoice_date': recurring_next_date,
                'payment_token_id': None})

            failing_subs |= subscription_mail_fail
            for dummy in range(5):
                failing_subs |= subscription_mail_fail.copy({'is_batch': True})
            failing_subs.action_confirm()
            # issue: two problems:
            # 1) payment failed, we want to avoid trigger it twice: (double cost) --> payment_exception
            # 2) batch: we need to avoid taking subscription two time. flag remains until the end of the last trigger
            failing_subs.order_line.qty_to_invoice = 1
            self.env['sale.order']._create_recurring_invoice(batch_size=3)
            self.assertFalse(self.mock_send_success_count)
            failing_result = [not res for res in failing_subs.mapped('payment_exception')]
            self.assertTrue(all(failing_result), "The subscription are not flagged anymore")
            failing_result = [not res for res in failing_subs.mapped('is_batch')]
            self.assertTrue(all(failing_result), "The subscription are not flagged anymore")
            failing_subs.payment_token_id = self.payment_token.id
            # Trigger the invoicing manually after fixing it
            failing_subs._create_recurring_invoice()
            vals = [sub.payment_exception for sub in failing_subs if sub.payment_exception]
            self.assertFalse(vals, "The subscriptions are not flagged anymore, the payment succeeded")

    def test_auto_payment_across_time(self):
        self.original_prepare_invoice = self.subscription._prepare_invoice

        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment), \
                patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._send_success_mail',
                      wraps=self._mock_subscription_send_success_mail):

            subscription_tmpl = self.env['sale.order.template'].create({
                'name': 'Subscription template without discount',
                'is_unlimited': False,
                'note': "This is the template description",
                'duration_value': 4,
                'duration_unit': 'month',
                'plan_id': self.plan_month.id,
            })

            self.subscription.write({
                'partner_id': self.partner.id,
                'company_id': self.company.id,
                'payment_token_id': self.payment_token.id,
                'sale_order_template_id': subscription_tmpl.id,
            })
            self.subscription._onchange_sale_order_template_id()
            self.mock_send_success_count = 0
            with freeze_time("2021-01-03"):
                self.subscription.order_line = [Command.clear()]
                self.subscription.write({
                    'start_date': False,
                    'next_invoice_date': False,
                    'order_line': [Command.create({'product_id': self.product.id,
                                                   'name': "month cheap",
                                                   'price_unit': 42,
                                                   'product_uom_qty': 2,
                                                   }),
                                   Command.create({'product_id': self.product2.id,
                                                   'name': "month expensive",
                                                   'price_unit': 420,
                                                   'product_uom_qty': 3,
                                                   }),
                                   ]}
                )
                self.subscription.action_confirm()
                self.assertEqual(self.subscription.end_date, datetime.date(2021, 5, 2))
                self.env['sale.order']._cron_recurring_create_invoice()
                invoice = self.subscription.invoice_ids.sorted('date')[-1]
                tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
                tx._reconcile_after_done()
                # Two products are invoiced
                self.assertEqual(len(invoice.invoice_line_ids), 2, 'Two lines are invoiced')
                self.assertEqual(self.subscription.next_invoice_date, datetime.date(2021, 2, 3), 'the next invoice date should be updated')
                self.assertEqual(invoice.invoice_line_ids[0].name, 'month cheap - 1 Months\n01/03/2021 to 02/02/2021', 'Invoice line description must be based on order line description')
                self.assertEqual(invoice.invoice_line_ids[1].name, 'month expensive - 1 Months\n01/03/2021 to 02/02/2021', 'Invoice line description must be based on order line description')

            with freeze_time("2021-02-03"):
                self.env.invalidate_all()
                self.env['sale.order']._cron_recurring_create_invoice()
                invoice = self.subscription.invoice_ids.sorted('date')[-1]
                tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
                invoice = self.subscription.invoice_ids.sorted('date')[-1]
                self.assertEqual(invoice.date, datetime.date(2021, 2, 3), 'We invoiced today')
                tx._reconcile_after_done()

            with freeze_time("2021-03-03"):
                self.env.invalidate_all()
                self.env['sale.order']._cron_recurring_create_invoice()
                invoice = self.subscription.invoice_ids.sorted('date')[-1]
                tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
                tx._reconcile_after_done()
                invoice = self.subscription.invoice_ids.sorted('date')[-1]
                self.assertEqual(invoice.date, datetime.date(2021, 3, 3), 'We invoiced today')

            # We continue
            with freeze_time("2021-04-03"):
                self.subscription.invalidate_recordset()
                self.env['sale.order']._cron_recurring_create_invoice()
                invoice = self.subscription.invoice_ids.sorted('date')[-1]
                tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
                tx._reconcile_after_done()
                invoice = self.subscription.invoice_ids.sorted('date')[-1]
                tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
                tx._reconcile_after_done()
                self.assertEqual(invoice.date, datetime.date(2021, 4, 3), 'We invoiced today')

            with freeze_time("2022-05-03"):
                self.subscription.invalidate_recordset(fnames=['subscription_state'])
                self.env['sale.order']._cron_recurring_create_invoice()
                self.assertEqual(self.subscription.subscription_state, '6_churn', 'the end_date is passed, the subscription is automatically closed')
                invoice = self.subscription.invoice_ids.sorted('date')[-1]
                self.assertEqual(invoice.date, datetime.date(2021, 4, 3), 'We should not create a new invoices')

    def test_do_payment_calls_send_payment_request_only_once(self):
        self.invoice = self.env['account.move'].create(
            self.subscription._prepare_invoice()
        )
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._send_payment_request'
        ) as patched:
            self.subscription._do_payment(self._create_token(), self.invoice)
            patched.assert_called_once()

    def test_payment_token_is_saved(self):
        """Tests that the payment token is saved when a quotation is paid"""
        portal_partner = self.user_portal.partner_id
        success_payment_template_id = self.subscription_tmpl.copy()
        subscription = self.env['sale.order'].create({
            'partner_id': portal_partner.id,
            'sale_order_template_id': success_payment_template_id.id,
        })
        subscription._onchange_sale_order_template_id()
        # send quotation
        subscription.action_quotation_sent()

        test_payment_token = self.env['payment.token'].create({
            'payment_details': 'Test',
            'partner_id': portal_partner.id,
            'provider_id': self.dummy_provider.id,
            'payment_method_id': self.payment_method_id,
            'provider_ref': 'test'
        })
        payment_with_token = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': subscription.amount_total,
            'date': subscription.date_order,
            'currency_id': subscription.currency_id.id,
            'partner_id': portal_partner.id,
            'payment_token_id': test_payment_token.id
        })

        transaction_ids = payment_with_token._create_payment_transaction()
        transaction_ids._set_done() # dummy transaction will always be successful

        subscription.write({'transaction_ids': [(6, 0, transaction_ids.ids)]})
        subscription.action_confirm()

        self.assertTrue(subscription.is_subscription)
        self.assertEqual(subscription.payment_token_id.id, test_payment_token.id)

    @mute_logger('odoo.addons.sale_subscription.models.sale_order')
    def test_exception_mail(self):
        self.subscription.write({'payment_token_id': self.payment_token.id,
                                 'client_order_ref': 'Customer REF XXXXXXX'
        })
        self.subscription.action_confirm()
        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', side_effect=Exception("Bad Token")), self.mock_mail_gateway():
            self.subscription._create_recurring_invoice()
        found_mail = self._find_mail_mail_wemail('accountman@test.com', 'sent', author=self.env.user.partner_id)
        mail_body = "<p>Error during renewal of contract [%s] Customer REF XXXXXXX Payment not recorded</p><p>Bad Token</p>" % self.subscription.id
        self.assertEqual(found_mail.body_html, mail_body)

    @mute_logger('odoo.addons.sale_subscription.models.sale_order')
    def test_bad_payment_exception(self):
        self.subscription.write({'payment_token_id': self.payment_token.id,
                                 'client_order_ref': 'Customer REF XXXXXXX'
        })
        self.subscription.action_confirm()

        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', side_effect=Exception("Oops, network error")),\
             self.mock_mail_gateway():
            self.subscription._create_recurring_invoice()

        invoice = self.subscription.order_line.invoice_lines.move_id
        self.assertFalse(invoice, "The draft invoice should be deleted when something goes wrong in _handle_automatic_invoices")
        self.assertEqual(
            self.subscription.next_invoice_date, self.subscription.start_date,
            "We should not have updated the next invoice date, as the invoice was unlinked",
        )

    @mute_logger('odoo.addons.sale_subscription.models.sale_order')
    def test_bad_payment_exception_post_success(self):
        self.subscription.write({'payment_token_id': self.payment_token.id,
                                 'client_order_ref': 'Customer REF XXXXXXX'
        })
        self.subscription.action_confirm()

        def _mock_subscription_do_payment_and_commit(payment_method, invoice, auto_commit=False):
            tx = self._mock_subscription_do_payment(payment_method, invoice, auto_commit=auto_commit)
            # once the payment request succeed, we're going to reconcile
            tx.env.cr.flush()  # simulate commit after sucessfull `_do_payment()`
            return tx

        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=_mock_subscription_do_payment_and_commit),\
             patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._subscription_post_success_payment', side_effect=Exception("Kaput")),\
             self.mock_mail_gateway():
            invoice = self.subscription._create_recurring_invoice()
            with self.assertRaises(Exception):
                invoice.transaction_ids._reconcile_after_done()

        invoice = self.subscription.order_line.invoice_lines.move_id
        self.assertTrue(
            invoice and invoice.state == "posted",
            "The draft invoice has to be kept as we committed after the payment succeeded "
            "(the next invoice date has already been updated)."
        )
        expected_next_invoice_date = self.subscription.start_date + self.subscription.plan_id.billing_period
        self.assertEqual(
            self.subscription.next_invoice_date, expected_next_invoice_date,
            "The next invoice date should have been updated, as the invoice was kept after the payment succeeded",
        )

    @mute_logger('odoo.addons.sale_subscription.models.sale_order')
    def test_bad_payment_rejected(self):
        self.subscription.write({'payment_token_id': self.payment_token.id,
                                 'client_order_ref': 'Customer REF XXXXXXX'
        })
        self.subscription.action_confirm()

        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment_rejected),\
             self.mock_mail_gateway():
            self.subscription._create_recurring_invoice()

        invoice = self.subscription.order_line.invoice_lines.move_id
        self.assertFalse(self.subscription.pending_transaction, "The pending transaction flag should not remain")
        self.assertFalse(invoice, "The draft invoice should be deleted when something goes wrong in _handle_automatic_invoices")
        self.assertEqual(
            self.subscription.next_invoice_date, self.subscription.start_date,
            "We should not have updated the next invoice date, as the invoice was unlinked",
        )

    def test_manual_invoice_with_token(self):
        self.subscription.write({'payment_token_id': self.payment_token.id,
                                 'client_order_ref': 'Customer REF XXXXXXX'
        })
        with freeze_time("2021-01-03"):
            self.subscription.action_confirm()
            self.subscription._create_invoices()
            self.subscription.order_line.invoice_lines.move_id._post()
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2021, 2, 3), 'the next invoice date should be updated')
            self.assertEqual(self.subscription.invoice_count, 1)

    def test_close_unpaid_contracts(self):
        with freeze_time("2022-01-01"):

            sub0 = self.env['sale.order'].create({
                'name': 'Paid',
                'partner_id': self.partner.id,
                'payment_term_id': self.env.ref('account.account_payment_term_21days').id,
                'sale_order_template_id': self.templ_5_days.id,
            })
            sub0._onchange_sale_order_template_id()
            sub0.action_confirm() # we these subs alone because they will be paid
            sub1 = sub0.copy(default={'name': 'Unpaid with simple date'})
            sub2 = sub1.copy(default={
                'name': "Partial",
                'payment_term_id': self.env.ref('account.account_payment_term_advance_60days').id})
            sub2.sale_order_template_id = self.templ_60_days.id
            sub3 = sub1.copy(default={
                'name': "Unpaid",
                'payment_term_id': self.env.ref('account.account_payment_term_advance_60days').id
            })
            sub4 = self.env['sale.order'].create({
                'name': 'Contract without template',
                'is_subscription': True,
                'plan_id': self.plan_year.id,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                    }),
                    (0, 0, {
                        'name': self.product2.name,
                        'product_id': self.product2.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                    })
                ]
            })
            all_subs = (sub1 | sub2 | sub3 | sub4).sorted('id')
            all_subs.origin_order_id = False
            for sub in all_subs - sub4:
                sub._onchange_sale_order_template_id()
            all_subs.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()
            # Make sure, the account_moves order corresponds to the subscription order.
            account_moves = sub1.invoice_ids | sub2.invoice_ids | sub3.invoice_ids | sub4.invoice_ids

        with freeze_time("2022-02-01"):
            self.env['account.payment.register'] \
                .with_context(active_model='account.move', active_ids=sub1.invoice_ids.ids) \
                .create({
                'currency_id': sub1.currency_id.id,
                'amount': 50,
            })._create_payments()
            self.assertEqual(sub1.invoice_ids.payment_state, 'partial')
            self.env['account.payment.register'] \
                .with_context(active_model='account.move',
                              active_ids=sub0.invoice_ids.ids).create(
                {
                    'currency_id': sub0.currency_id.id,
                    'amount': 400,
                })._create_payments()

            self.assertTrue(sub0.invoice_ids.payment_state in ['in_payment', 'paid'])
            self.assertEqual(account_moves.mapped('payment_state'), ['partial', 'not_paid', 'not_paid', 'not_paid'])
            template_limit = {account_moves[0].id: 5, account_moves[1].id: 60, account_moves[2].id: 5, account_moves[3].id: 15}
            date_data = [(aml.date_maturity,
                          aml.date_maturity + relativedelta(days=template_limit[aml.move_id.id]),
                          aml.move_id.id,
                          aml.move_id.invoice_line_ids.sale_line_ids.order_id.name) for aml in account_moves.line_ids.filtered('date_maturity')]
            self.assertEqual(date_data, [
                (datetime.date(2022, 1, 22), datetime.date(2022, 1, 27), account_moves[0].id, 'Unpaid with simple date'),
                (datetime.date(2022, 1, 1), datetime.date(2022, 3, 2), account_moves[1].id, 'Partial'),
                (datetime.date(2022, 3, 2), datetime.date(2022, 5, 1), account_moves[1].id, 'Partial'),
                (datetime.date(2022, 1, 1), datetime.date(2022, 1, 6), account_moves[2].id, 'Unpaid'),
                (datetime.date(2022, 3, 2), datetime.date(2022, 3, 7), account_moves[2].id, 'Unpaid'),
                (datetime.date(2022, 1, 1), datetime.date(2022, 1, 16), account_moves[3].id, 'Contract without template'),
            ])

        with freeze_time("2022-02-01"):
            self.env['sale.order'].sudo()._cron_subscription_expiration()
            self.assertEqual(all_subs.mapped('subscription_state'), ['3_progress', '3_progress', '3_progress', '6_churn'], "First and last invoices are never paid")

        with freeze_time("2022-03-08"):
            self.env['sale.order'].sudo()._cron_subscription_expiration()
            self.assertEqual(all_subs.mapped('subscription_state'), ['3_progress', '3_progress', '6_churn', '6_churn'],
                             "Unpaid payment expire on 2022-03-02 +  5days = 2022-03-07")

        with freeze_time("2022-05-02"):
            self.env['sale.order'].sudo()._cron_subscription_expiration()
            self.assertEqual(account_moves.mapped('payment_state'), ['partial', 'not_paid', 'not_paid', 'not_paid'])
            self.assertEqual(all_subs.mapped('subscription_state'), ['3_progress', '6_churn', '6_churn', '6_churn'])
            self.assertEqual(sub3.close_reason_id.id, self.env.ref("sale_subscription.close_reason_unpaid_subscription").id)
            self.assertEqual(sub0.subscription_state, '3_progress')

        with freeze_time("2023-01-07"):
            # No new invoice, we don't increment the next_invoice_date
            self.env['sale.order'].sudo()._cron_subscription_expiration()
            self.assertEqual(sub0.subscription_state, '6_churn')

    def test_close_unpaid_contracts_bis(self):
        # We don't close the contract if the last invoice is paid but the invoice before was not paid
        with freeze_time("2023-01-01"):

            sub = self.env['sale.order'].create({
                'name': 'Paid',
                'partner_id': self.partner.id,
                'payment_term_id': self.env.ref('account.account_payment_term_21days').id,
                'sale_order_template_id': self.templ_5_days.id,
            })
            sub._onchange_sale_order_template_id()
            sub.action_confirm()  # we these subs alone because they will be paid

            # We don't pay tbis invoice to simulate bad historical data
            self.env['sale.order']._cron_recurring_create_invoice()
            invoice_to_skip = sub.invoice_ids
        with freeze_time("2024-01-01"):
            self.env['sale.order']._cron_recurring_create_invoice()
            invoice_to_pay = sub.invoice_ids - invoice_to_skip
            self.env['account.payment.register'] \
                .with_context(active_model='account.move',
                              active_ids=invoice_to_pay.ids).create(
                {
                    'currency_id': sub.currency_id.id,
                    'amount': 300,
                })._create_payments()
        # If the last invoice is paid, we don't close the contract
        with freeze_time("2025-01-02"):
            self.env['sale.order'].sudo()._cron_subscription_expiration()
            self.assertEqual(sub.subscription_state, '3_progress')
        # The contract is expired, the next invoice date is passed since 5 days, we close it
        with freeze_time("2025-01-07"):
            self.env['sale.order'].sudo()._cron_subscription_expiration()
            self.assertEqual(sub.subscription_state, '6_churn')
            self.assertEqual(sub.close_reason_id.id, self.env.ref("sale_subscription.close_reason_auto_close_limit_reached").id)

    def test_partial_payment(self):
        subscription = self.subscription
        subscription.action_confirm()

        # /payment/pay will create a transaction, validate it and post-process-it
        reference = "CONTRACT-%s-%s" % (subscription.id, datetime.datetime.now().strftime('%y%m%d_%H%M%S%f'))
        values = {
            'amount': subscription.amount_total / 2.,  # partial amount
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'operation': 'offline',
            'currency_id': subscription.currency_id.id,
            'reference': reference,
            'token_id': False,
            'partner_id': subscription.partner_id.id,
            'partner_country_id': subscription.partner_id.country_id.id,
            'invoice_ids': [],
            'sale_order_ids': [(6, 0, subscription.ids)],
            'state': 'draft',
        }
        tx = self.env["payment.transaction"].create(values)
        tx._set_done()
        tx._finalize_post_processing()

        self.assertEqual(tx.state, 'done')
        self.assertFalse(tx.invoice_ids, "We should not have created an invoice")
        self.assertFalse(subscription.invoice_ids, "We should not have created an invoice on the subscription")
        self.assertEqual(
            subscription.start_date, subscription.next_invoice_date,
            "The subscription next invoice date should not have been updated"
        )

    def test_refund_next_invoice_date(self):
        with freeze_time('2023-01-18'):
            subscription = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 3.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
            })
            subscription.action_confirm()
            subscription._create_recurring_invoice()
            self.assertEqual(subscription.next_invoice_date, datetime.date(2023, 2, 18), "The next invoice date is incremented")
            subscription._get_invoiced()
            inv = subscription.invoice_ids

            test_payment_token = self.env['payment.token'].create({
                'payment_details': 'Test',
                'partner_id': subscription.partner_id.id,
                'provider_id': self.dummy_provider.id,
                'payment_method_id': self.payment_method_id,
                'provider_ref': 'test'
            })
            payment_with_token = self.env['account.payment'].create({
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'amount': subscription.amount_total,
                'date': subscription.date_order,
                'currency_id': subscription.currency_id.id,
                'partner_id': subscription.partner_id.id,
                'payment_token_id': test_payment_token.id
            })
            transaction_ids = payment_with_token._create_payment_transaction()
            transaction_ids._set_done()  # dummy transaction will always be successful
            with freeze_time('2023-02-18'):
                subscription._create_recurring_invoice()
                self.assertEqual(subscription.next_invoice_date, datetime.date(2023, 3, 18), "The next invoice date is incremented")
            # We refund the first invoice
            refund_wizard = self.env['account.move.reversal'].with_context(
                active_model="account.move",
                active_ids=inv.ids).create({
                'reason': 'Test refund tax repartition',
                'journal_id': inv.journal_id.id,
            })
            res = refund_wizard.refund_moves()
            refund_move = self.env['account.move'].browse(res['res_id'])
            self.assertEqual(inv.reversal_move_id, refund_move, "The initial move should be reversed")
            self.assertEqual(subscription.next_invoice_date, datetime.date(2023, 3, 18), "The next invoice date not incremented")

    def test_subscription_invoice_after_payment(self):
        self.amount = self.subscription.amount_total
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.subscription.id], state='done')
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._reconcile_after_done()
        self.assertEqual(self.subscription.state, 'sale')
        self.assertEqual(len(self.subscription.invoice_ids), 1)
        self.assertEqual(self.subscription.invoice_ids.state, 'posted')

    def test_manually_captured_payment_providers_not_allowed(self):
        self.provider.capture_manually = True

        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=self.subscription.id
        )

        self.assertNotIn(self.provider, compatible_providers)

    def test_cancel_draft_invoice_unsuccessful_transaction(self):
        """ Ensure that after an unsuccessful token payment is made, its draft invoice is canceled. """
        with freeze_time("2024-01-23"):
            subscription = self.env['sale.order'].create({
                'partner_id': self.user_portal.partner_id.id,
                'sale_order_template_id': self.subscription_tmpl.id,
                'start_date': datetime.date(2024, 1, 15)
            })
            subscription._onchange_sale_order_template_id()
            test_payment_token = self.env['payment.token'].create({
                'payment_details': 'Test',
                'partner_id': self.user_portal.partner_id.id,
                'provider_id': self.dummy_provider.id,
                'payment_method_id': self.payment_method_id,
                'provider_ref': 'test'
            })
            payment_with_token = self.env['account.payment'].create({
                'amount': subscription.amount_total,
                'currency_id': subscription.currency_id.id,
                'partner_id': self.user_portal.partner_id.id,
                'payment_token_id': test_payment_token.id
            })
            transaction_ids = payment_with_token._create_payment_transaction()
            subscription.write({'transaction_ids': [Command.set(transaction_ids.ids)]})
            subscription.action_confirm()
            subscription._create_invoices(final=True)
            draft_invoice = subscription.order_line.invoice_lines.move_id.filtered(lambda am: am.state == 'draft')
            transaction_ids._set_error("Payment declined!")
            self.assertEqual(len(draft_invoice), 1, "A single draft invoice must be created after the payment was done.")
            self.assertFalse(subscription.pending_transaction, "Subscription doesn't have pending transaction after unsuccessful payment.")
            self.assertFalse(subscription.payment_token_id, "The payment token should not be saved after the unsuccessful payment.")
            self.assertEqual(draft_invoice.state, "cancel", "Draft invoice must be canceled after unsuccessful payment.")
