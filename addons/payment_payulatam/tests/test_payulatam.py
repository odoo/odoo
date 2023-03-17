# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time
from werkzeug.exceptions import Forbidden

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_payulatam.controllers.main import PayuLatamController
from odoo.addons.payment_payulatam.models.payment_provider import SUPPORTED_CURRENCIES
from odoo.addons.payment_payulatam.tests.common import PayULatamCommon


@tagged('post_install', '-at_install')
class PayULatamTest(PayULatamCommon, PaymentHttpCommon):

    def test_compatibility_with_supported_currencies(self):
        """ Test that the PayULatam provider is compatible with all supported currencies. """
        for supported_currency_code in SUPPORTED_CURRENCIES:
            supported_currency = self._prepare_currency(supported_currency_code)
            compatible_providers = self.env['payment.provider']._get_compatible_providers(
                self.company.id, self.partner.id, self.amount, currency_id=supported_currency.id
            )
            self.assertIn(self.payulatam, compatible_providers)

    def test_incompatibility_with_unsupported_currency(self):
        """ Test that the PayULatam provider is not compatible with an unsupported currency. """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertNotIn(self.payulatam, compatible_providers)

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_reference_is_singularized(self):
        """ Test singularization of reference prefixes. """
        reference = self.env['payment.transaction']._compute_reference(self.payulatam.code)
        self.assertEqual(
            reference, 'tx-20111102120021', "transaction reference was not correctly singularized"
        )

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_reference_is_computed_based_on_document_name(self):
        """ Test computation of reference prefixes based on the provided invoice. """
        self._skip_if_account_payment_is_not_installed()

        invoice = self.env['account.move'].create({})
        reference = self.env['payment.transaction']._compute_reference(
            self.payulatam.code, invoice_ids=[Command.set([invoice.id])]
        )
        self.assertEqual(reference, 'MISC/2011/11/0001-20111102120021')

    def test_redirect_form_values(self):
        """ Test the values of the redirect form inputs. """
        tx = self._create_transaction(flow='redirect')
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
            'confirmationUrl': self._build_url(PayuLatamController._webhook_url),
            'test': str(1),  # testing is always performed in test mode
        }
        expected_values['signature'] = self.payulatam._payulatam_generate_sign(
            expected_values, incoming=False
        )

        self.assertEqual(
            form_info['action'], 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/'
        )
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
            self.env['payment.transaction']._handle_notification_data(
                'payulatam', payulatam_post_data
            )

        tx = self._create_transaction(flow='redirect')

        # Validate the transaction ('pending' state)
        self.env['payment.transaction']._handle_notification_data('payulatam', payulatam_post_data)
        self.assertEqual(tx.state, 'pending', 'Payulatam: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.state_message, payulatam_post_data['message'], 'Payulatam: wrong state message after receiving a valid pending notification')
        self.assertEqual(tx.provider_reference, 'b232989a-4aa8-42d1-bace-153236eee791', 'Payulatam: wrong txn_id after receiving a valid pending notification')

        # Reset the transaction
        tx.write({
            'state': 'draft',
            'provider_reference': False})

        # Validate the transaction ('approved' state)
        payulatam_post_data['lapTransactionState'] = 'APPROVED'
        self.env['payment.transaction']._handle_notification_data('payulatam', payulatam_post_data)
        self.assertEqual(tx.state, 'done', 'Payulatam: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.provider_reference, 'b232989a-4aa8-42d1-bace-153236eee791', 'Payulatam: wrong txn_id after receiving a valid pending notification')

    @mute_logger('odoo.addons.payment_payulatam.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(PayuLatamController._webhook_url)
        self._make_http_post_request(url, data=self.async_notification_data_webhook)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_payulatam.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(PayuLatamController._webhook_url)
        with patch(
            'odoo.addons.payment_payulatam.controllers.main.PayuLatamController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_http_post_request(url, data=self.async_notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """ Test the verification of a notification with a valid signature. """
        tx = self._create_transaction('redirect')
        payload = PayuLatamController._normalize_data_keys(self.async_notification_data)
        self._assert_does_not_raise(
            Forbidden, PayuLatamController._verify_notification_signature, payload, tx
        )

    @mute_logger('odoo.addons.payment_payulatam.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        payload = PayuLatamController._normalize_data_keys(
            dict(self.async_notification_data, sign=None)
        )
        self.assertRaises(
            Forbidden, PayuLatamController._verify_notification_signature, payload, tx
        )

    @mute_logger('odoo.addons.payment_payulatam.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        payload = PayuLatamController._normalize_data_keys(
            dict(self.async_notification_data, sign='dummy')
        )
        self.assertRaises(
            Forbidden, PayuLatamController._verify_notification_signature, payload, tx
        )
