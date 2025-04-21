# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.urls import url_encode

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_xendit.controllers.main import XenditController
from odoo.addons.payment_xendit.models.payment_provider import PaymentProvider
from odoo.addons.payment_xendit.tests.common import XenditCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(PaymentHttpCommon, XenditCommon):

    def test_no_item_missing_from_rendering_values(self):
        """ Test that when the redirect flow is triggered, rendering_values contains the
        API_URL corresponding to the response of API request. """
        tx = self._create_transaction('redirect')
        url = 'https://dummy.com'
        return_value = {'invoice_url': url}
        with (
            patch.object(PaymentProvider, '_xendit_make_request', return_value=return_value),
            patch.object(payment_utils, 'generate_access_token', self._generate_test_access_token),
        ):
            rendering_values = tx._get_specific_rendering_values(None)
        self.assertDictEqual(rendering_values, {'api_url': url})

    def test_empty_rendering_values_if_direct(self):
        """ Test that if it's a card payment (like in direct flow), rendering_values should be empty
        and no API call should be committed in the process. """
        card_pm = self.env.ref('payment.payment_method_card').id
        tx = self._create_transaction('direct', payment_method_id=card_pm)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value={'data': {'link': 'https://dummy.com'}}
        ) as mock:
            rendering_values = tx._get_specific_rendering_values(None)
            self.assertEqual(mock.call_count, 0)
        self.assertDictEqual(rendering_values, {})

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that the `api_url` key is not omitted from the rendering values. """
        tx = self._create_transaction('redirect')
        with patch(
            'odoo.addons.payment_xendit.models.payment_transaction.PaymentTransaction'
            '._get_specific_rendering_values', return_value={'api_url': 'https://dummy.com'}
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], 'https://dummy.com')
        self.assertEqual(form_info['method'], 'get')
        self.assertDictEqual(form_info['inputs'], {})

    def test_no_item_missing_from_invoice_request_payload(self):
        """ Test that the invoice request values are conform to the transaction fields. """
        self.maxDiff = 10000  # Allow comparing large dicts.
        self.reference = 'tx1'
        tx = self._create_transaction(flow='redirect')
        return_url = self._build_url(XenditController._return_url)
        access_token = self._generate_test_access_token(tx.reference, tx.amount)
        success_url_params = url_encode({
            'tx_ref': tx.reference,
            'access_token': access_token,
            'success': 'true',
        })

        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            request_payload = tx._xendit_prepare_invoice_request_payload()
        self.assertDictEqual(request_payload, {
            'external_id': tx.reference,
            'amount': tx.amount,
            'description': tx.reference,
            'customer': {
                'given_names': tx.partner_name,
                'email': tx.partner_email,
                'mobile_number': tx.partner_id.phone,
                'addresses': [{
                    'city': tx.partner_city,
                    'country': tx.partner_country_id.name,
                    'postal_code': tx.partner_zip,
                    'street_line1': tx.partner_address,
                }],
            },
            'success_redirect_url': f'{return_url}?{success_url_params}',
            'failure_redirect_url': return_url,
            'payment_methods': [self.payment_method_code.upper()],
            'currency': tx.currency_id.name,
        })

    def test_processing_values_contain_rounded_amount_idr(self):
        """ Ensure that for IDR currency, processing_values should contain converted_amount
        which is the amount rounded down to the nearest 0."""
        currency_idr = self.env.ref('base.IDR')
        tx = self._create_transaction('redirect', amount=1000.50, currency_id=currency_idr.id)
        processing_values = tx._get_specific_processing_values({})
        self.assertEqual(processing_values.get('rounded_amount'), 1000)

    def test_charge_request_contains_rounded_amount_idr(self):
        """ Ensure that for IDR currency, when creating charge API, the amount in payload
        should be rounded down to the nearest 0 """
        currency_idr = self.env.ref('base.IDR')
        tx = self._create_transaction('redirect', amount=1000.50, currency_id=currency_idr.id)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.charge_notification_data
        ) as mock_req:
            tx._xendit_create_charge('dummytoken')
            payload = mock_req.call_args.kwargs.get('payload')
            self.assertEqual(payload['amount'], 1000)

    def test_get_tx_from_notification_data_returns_tx(self):
        """ Test that the transaction is found based on the notification data. """
        tx = self._create_transaction('redirect')
        tx_found = self.env['payment.transaction']._get_tx_from_notification_data(
            'xendit', self.webhook_notification_data
        )
        self.assertEqual(tx, tx_found)

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction('redirect')
        tx._process_notification_data(self.webhook_notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_processing_notification_data_tokenizes_transaction(self):
        """ Test that the transaction is tokenized when a charge request is successfully made on a
        transaction that saves payment details. """
        tx = self._create_transaction('direct', tokenize=True)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.charge_notification_data
        ), patch(
            'odoo.addons.payment_xendit.models.payment_transaction.PaymentTransaction'
            '._xendit_tokenize_from_notification_data'
        ) as tokenize_mock:
            tx._xendit_create_charge('dummytoken')
            self.assertEqual(tokenize_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_tokenization_flow_not_save_payment_details(self):
        """ Test that `_xendit_tokenize_from_notification_data` would not be triggered on a
        transaction that doesn't save the payment details. """
        tx = self._create_transaction('direct')
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider.'
            '_xendit_make_request', return_value=self.charge_notification_data
        ), patch(
            'odoo.addons.payment_xendit.models.payment_transaction.PaymentTransaction.'
            '_xendit_tokenize_from_notification_data'
        ) as tokenize_check_mock:
            tx._xendit_create_charge('dummytoken')
            self.assertEqual(tokenize_check_mock.call_count, 0)
