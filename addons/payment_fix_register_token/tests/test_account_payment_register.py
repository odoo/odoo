# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountPaymentRegister(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.pay_method_electronic = cls.env.ref('payment.account_payment_method_electronic_in')

        cls.partner_a.country_id = cls.env.ref('base.us')

        cls.pay_acquirer = cls.env['payment.acquirer'].create({
            'name': "Dummy acquirer",
            'provider': 'manual',
            'company_id': cls.env.company.id,
        })

        cls.pay_token = cls.env['payment.token'].create({
            'name': "Dummy Token",
            'partner_id': cls.partner_a.id,
            'acquirer_id': cls.pay_acquirer.id,
            'acquirer_ref': "TEST",
        })

    def test_register_payment_electronic(self):

        def _s2s_do_transaction_mock(_self, **_kwargs):
            _self.state = 'done'

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 1000.0})],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{'amount_residual': 1000.0}])

        with patch(
            'odoo.addons.payment.models.payment_acquirer.PaymentTransaction.s2s_do_transaction',
            new=_s2s_do_transaction_mock,
        ):
            payments = self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({
                    'payment_method_id': self.pay_method_electronic.id,
                    'payment_token_id': self.pay_token.id,
                })\
                ._create_payments()

        self.assertRecordValues(payments.payment_transaction_id, [{'invoice_ids': invoice.ids}])
        self.assertRecordValues(invoice, [{'amount_residual': 0.0}])
