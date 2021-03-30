# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import PayulatamCommon
from ..controllers.main import PayuLatamController
from ..models.payment_acquirer import SUPPORTED_CURRENCIES


@tagged('post_install', '-at_install')
class PayUlatamTest(PayulatamCommon):

    def test_compatible_acquirers(self):
        for curr in SUPPORTED_CURRENCIES:
            currency = self._prepare_currency(curr)
            acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
                partner_id=self.partner.id,
                company_id=self.company.id,
                currency_id=currency.id,
            )
            self.assertIn(self.payulatam, acquirers)

        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            company_id=self.company.id,
            currency_id=self.currency_euro.id,
        )
        self.assertNotIn(self.payulatam, acquirers)

    # freeze time for consistent singularize_prefix behavior during the test
    @freeze_time("2011-11-02 12:00:21")
    def test_reference(self):
        tx = self.create_transaction(flow="redirect", reference="")
        self.assertEqual(tx.reference, "tx-20111102120021",
            "Payulatam: transaction reference wasn't correctly singularized.")

    def test_redirect_form_values(self):
        tx = self.create_transaction(flow='redirect')
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()

        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        expected_values = {
            'merchantId': 'dummy',
            'accountId': 'dummy',
            'description': self.reference,
            'referenceCode': self.reference,
            'amount': str(self.amount),
            'currency': self.currency.name,
            'tax': str(0),
            'taxReturnBase': str(0),
            'buyerEmail': self.partner.email,
            'buyerFullName': self.partner.name,
            'responseUrl': self._build_url(PayuLatamController._return_url),
            'test': str(1), # test is always done in test mode.
        }
        expected_values['signature'] = self.payulatam._payulatam_generate_sign(
            expected_values, incoming=False)

        self.assertEqual(form_info['action'],
            'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/')
        self.assertDictEqual(form_info['inputs'], expected_values)

    def test_feedback_processing(self):
        # typical data posted by payulatam after client has successfully paid
        payulatam_post_data = {
            'installmentsNumber': '1',
            'lapPaymentMethod': 'VISA',
            'description': self.reference,
            'currency': self.currency.name,
            'extra2': '',
            'lng': 'es',
            'transactionState': '7',
            'polPaymentMethod': '211',
            'pseCycle': '',
            'pseBank': '',
            'referenceCode': self.reference,
            'reference_pol': '844164756',
            'signature': 'f3ea3a7414a56d8153c425ab7e2f69d7',  # Update me
            'pseReference3': '',
            'buyerEmail': 'admin@yourcompany.example.com',
            'lapResponseCode': 'PENDING_TRANSACTION_CONFIRMATION',
            'pseReference2': '',
            'cus': '',
            'orderLanguage': 'es',
            'TX_VALUE': str(self.amount),
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

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._handle_feedback_data('payulatam', payulatam_post_data)

        tx = self.create_transaction(flow='redirect')

        # Validate the transaction ('pending' state)
        self.env['payment.transaction']._handle_feedback_data('payulatam', payulatam_post_data)
        self.assertEqual(tx.state, 'pending', 'Payulatam: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.state_message, payulatam_post_data['message'], 'Payulatam: wrong state message after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, 'b232989a-4aa8-42d1-bace-153236eee791', 'Payulatam: wrong txn_id after receiving a valid pending notification')

        # Reset the transaction
        tx.write({
            'state': 'draft',
            'acquirer_reference': False})

        # Validate the transaction ('approved' state)
        payulatam_post_data['lapTransactionState'] = 'APPROVED'
        self.env['payment.transaction']._handle_feedback_data('payulatam', payulatam_post_data)
        self.assertEqual(tx.state, 'done', 'Payulatam: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, 'b232989a-4aa8-42d1-bace-153236eee791', 'Payulatam: wrong txn_id after receiving a valid pending notification')
