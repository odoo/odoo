# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import objectify
from werkzeug import urls

from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.tests import tagged


class PayUlatamCommon(PaymentAcquirerCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.payulatam = cls.env.ref('payment.payment_acquirer_payulatam')
        cls.payulatam.write({
            'payulatam_account_id': 'dummy',
            'payulatam_merchant_id': 'dummy',
            'payulatam_api_key': 'dummy',
            'state': 'test',
        })


@tagged('post_install', '-at_install', 'external', '-standard')
class PayUlatamForm(PayUlatamCommon):

    def test_10_payulatam_form_render(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        self.assertEqual(self.payulatam.state, 'test', 'test without test environment')
        self.payulatam.write({
            'payulatam_merchant_id': 'dummy',
            'payulatam_account_id': 'dummy',
            'payulatam_api_key': 'dummy',
        })

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------
        self.env['payment.transaction'].create({
            'reference': 'test_ref0',
            'amount': 0.001,
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.payulatam.id,
            'partner_id': self.buyer_id
        })

        # render the button
        res = self.payulatam.render(
            'test_ref0', 0.01, self.currency_euro.id,
            values=self.buyer_values)

        form_values = {
            'merchantId': 'dummy',
            'accountId': 'dummy',
            'description': 'test_ref0',
            'referenceCode': 'test',
            'amount': '0.01',
            'currency': 'EUR',
            'tax': '0',
            'taxReturnBase': '0',
            'buyerEmail': 'norbert.buyer@example.com',
            'responseUrl': urls.url_join(base_url, '/payment/payulatam/response'),
            'extra1': None
        }
        # check form result
        tree = objectify.fromstring(res)

        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(len(data_set), 1, 'payulatam: Found %d "data_set" input instead of 1' % len(data_set))
        self.assertEqual(data_set[0].get('data-action-url'), 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/', 'payulatam: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit', 'data_set', 'signature', 'referenceCode']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'payulatam: wrong value for input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    def test_20_payulatam_form_management(self):
        self.assertEqual(self.payulatam.state, 'test', 'test without test environment')

        # typical data posted by payulatam after client has successfully paid
        payulatam_post_data = {
            'installmentsNumber': '1',
            'lapPaymentMethod': 'VISA',
            'description': 'test_ref0',
            'currency': 'EUR',
            'extra2': '',
            'lng': 'es',
            'transactionState': '7',
            'polPaymentMethod': '211',
            'pseCycle': '',
            'pseBank': '',
            'referenceCode': 'test_ref_10',
            'reference_pol': '844164756',
            'signature': '88f11d693d3551419f86850948d731ba',
            'pseReference3': '',
            'buyerEmail': 'admin@yourcompany.example.com',
            'lapResponseCode': 'PENDING_TRANSACTION_CONFIRMATION',
            'pseReference2': '',
            'cus': '',
            'orderLanguage': 'es',
            'TX_VALUE': '0.01',
            'risk': '',
            'trazabilityCode': '',
            'extra3': '',
            'pseReference1': '',
            'polTransactionState': '14',
            'polResponseCode': '25',
            'merchant_name': 'Test PayU Test comercio',
            'merchant_url': 'http://pruebaslapv.xtrweb.com',
            'extra1': '/shop/payment/validate',
            'message': 'PENDING',
            'lapPaymentMethodType': 'CARD',
            'polPaymentMethodType': '7',
            'telephone': '7512354',
            'merchantId': 'dummy',
            'transactionId': 'b232989a-4aa8-42d1-bace-153236eee791',
            'authorizationCode': '',
            'lapTransactionState': 'PENDING',
            'TX_TAX': '.00',
            'merchant_address': 'Av 123 Calle 12'
        }

        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': 0.01,
            'acquirer_id': self.payulatam.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_10',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id,
            'partner_id': self.buyer_id})

        # validate transaction
        tx.form_feedback(payulatam_post_data, 'payulatam')
        # check
        self.assertEqual(tx.state, 'pending', 'Payulatam: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.state_message, 'PENDING', 'Payulatam: wrong state message after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, 'b232989a-4aa8-42d1-bace-153236eee791', 'PayU Latam: wrong txn_id after receiving a valid pending notification')

        # update transaction
        tx.write({
            'state': 'draft',
            'acquirer_reference': False})

        # update notification from payulatam
        payulatam_post_data['lapTransactionState'] = 'APPROVED'
        # validate transaction
        tx.form_feedback(payulatam_post_data, 'payulatam')
        # check transaction
        self.assertEqual(tx.state, 'done', 'payulatam: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, 'b232989a-4aa8-42d1-bace-153236eee791', 'payulatam: wrong txn_id after receiving a valid pending notification')
