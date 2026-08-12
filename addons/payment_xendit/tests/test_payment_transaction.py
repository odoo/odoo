# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from uuid import UUID

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
        return_value = {'payment_link_url': url}
        with (
            patch.object(PaymentProvider, '_xendit_make_request', return_value=return_value),
            patch.object(payment_utils, 'generate_access_token', self._generate_test_access_token),
        ):
            rendering_values = tx._get_specific_rendering_values(None)
        self.assertDictEqual(rendering_values, {'api_url': url})

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that the `api_url` key is not omitted from the rendering values. """
        tx = self._create_transaction('redirect')
        with patch(
            'odoo.addons.payment_xendit.models.payment_transaction.PaymentTransaction'
            '._get_specific_rendering_values', return_value={'api_url': 'https://dummy.com'}
        ), patch(
            'odoo.addons.payment.utils.generate_access_token',
            new=self._generate_test_access_token
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], 'https://dummy.com')
        self.assertEqual(form_info['method'], 'get')
        self.assertDictEqual(form_info['inputs'], {})

    def test_no_item_missing_from_session_request_payload(self):
        """ Test that the session request values are conform to the transaction fields. """
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

        test_uuid = UUID('12345678-1234-5678-1234-567812345678')
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ), patch(
            'odoo.addons.payment_xendit.models.payment_transaction.uuid4', return_value=test_uuid
        ):
            request_payload = tx._xendit_prepare_session_request_payload()
        partner_first_name, partner_last_name = payment_utils.split_partner_name(tx.partner_name)
        self.assertDictEqual(request_payload, {
            'reference_id': tx.reference,
            'session_type': 'PAY',
            'mode': 'PAYMENT_LINK',
            'amount': tx.amount,
            'description': tx.reference,
            'customer': {
                'reference_id': f'customer{tx.partner_id.id}{test_uuid.hex[:8]}',
                'type': 'INDIVIDUAL',
                'individual_detail': {
                    'given_names': partner_first_name,
                    'surname': partner_last_name,
                },
                'email': tx.partner_email,
                'mobile_number': '003212345678',
            },
            'success_return_url': f'{return_url}?{success_url_params}',
            'cancel_return_url': return_url,
            'allowed_payment_channels': [self.payment_method_code.upper()],
            'currency': tx.currency_id.name,
            'country': tx.partner_id.country_id.code,
        })

    def test_card_session_payload_with_tokenization(self):
        """ Test that card session payload includes tokenization settings when tokenize is set. """
        card_pm = self.env.ref('payment.payment_method_card').id
        tx = self._create_transaction('redirect', payment_method_id=card_pm, tokenize=True)
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            request_payload = tx._xendit_prepare_session_request_payload()
        self.assertEqual(request_payload['session_type'], 'PAY')
        self.assertEqual(request_payload['allow_save_payment_method'], 'FORCED')
        self.assertEqual(
            request_payload['channel_properties'],
            {'cards': {'card_on_file_type': 'CUSTOMER_UNSCHEDULED'}},
        )
        self.assertEqual(request_payload['allowed_payment_channels'], ['CARDS'])

    def test_card_session_payload_without_tokenization(self):
        """ Test that card session payload has no tokenization settings without tokenize. """
        card_pm = self.env.ref('payment.payment_method_card').id
        tx = self._create_transaction('redirect', payment_method_id=card_pm)
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            request_payload = tx._xendit_prepare_session_request_payload()
        self.assertNotIn('allow_save_payment_method', request_payload)
        self.assertNotIn('channel_properties', request_payload)

    def test_validation_session_payload_is_save(self):
        """ Test that validation operations create a SAVE session with zero amount. """
        card_pm = self.env.ref('payment.payment_method_card').id
        tx = self._create_transaction(
            'redirect', operation='validation', payment_method_id=card_pm
        )
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            request_payload = tx._xendit_prepare_session_request_payload()
        self.assertEqual(request_payload['session_type'], 'SAVE')
        self.assertEqual(request_payload['amount'], 0)

    def test_processing_values_contain_rounded_amount_idr(self):
        """ Ensure that for IDR currency, processing_values should contain converted_amount
        which is the amount rounded down to the nearest 0."""
        currency_idr = self.env.ref('base.IDR')
        tx = self._create_transaction('redirect', amount=1000.50, currency_id=currency_idr.id)
        with patch(
            'odoo.addons.payment.utils.generate_access_token',
            new=self._generate_test_access_token
        ):
            processing_values = tx._get_specific_processing_values({})
        self.assertEqual(processing_values.get('rounded_amount'), 1000)

    def test_get_pending_authentication_url_when_requires_action(self):
        """ Test that the authentication URL is returned for a token payment stuck in
        REQUIRES_ACTION, as Xendit can challenge card-on-file charges with 3DS. """
        tx = self._create_transaction('token')
        tx._process_notification_data(self.payment_request_requires_action_data)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.payment_request_requires_action_data
        ) as mock_req:
            auth_url = tx._xendit_get_pending_authentication_url()
        self.assertEqual(
            auth_url, self.payment_request_requires_action_data['actions'][0]['value']
        )
        self.assertEqual(
            mock_req.call_args.args[0], 'v3/payment_requests/pr-64a8d9c614802d6c402cd82d'
        )
        self.assertEqual(mock_req.call_args.kwargs.get('method'), 'GET')
        self.assertEqual(mock_req.call_args.kwargs.get('api_version'), '2024-11-11')

    def test_get_pending_authentication_url_when_not_pending(self):
        """ Test that no authentication URL is returned, and no API call made, for a
        transaction that isn't pending. """
        tx = self._create_transaction('token')
        tx._process_notification_data(self.payment_request_notification_data)  # status SUCCEEDED
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request'
        ) as mock_req:
            auth_url = tx._xendit_get_pending_authentication_url()
        self.assertIsNone(auth_url)
        self.assertEqual(mock_req.call_count, 0)

    def test_get_pending_authentication_url_when_status_not_requires_action(self):
        """ Test that no authentication URL is returned when the payment request isn't (or is
        no longer) awaiting customer action. """
        tx = self._create_transaction('token')
        tx._process_notification_data(self.payment_request_requires_action_data)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.payment_request_notification_data
        ):
            auth_url = tx._xendit_get_pending_authentication_url()
        self.assertIsNone(auth_url)

    def test_processing_values_include_redirect_form_when_authentication_required(self):
        """ Test that processing values for a token payment include the authentication URL when
        the charge requires 3DS authentication. """
        tx = self._create_transaction('token')
        tx._process_notification_data(self.payment_request_requires_action_data)
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ), patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.payment_request_requires_action_data
        ):
            processing_values = tx._get_specific_processing_values({})
        self.assertEqual(
            processing_values['pending_authentication_url'],
            self.payment_request_requires_action_data['actions'][0]['value'],
        )

    def test_no_item_missing_from_token_charge_payload(self):
        """ Test that the token charge is sent to the payment_requests endpoint with the expected
        payload: notably, no skip_three_ds (it requires a dashboard feature most merchants don't
        have activated and isn't needed for card-on-file charges), and the amount rounded down to
        the currency's supported precision. """
        currency_idr = self.env.ref('base.IDR')
        tx = self._create_transaction('redirect', amount=1000.50, currency_id=currency_idr.id)
        return_url = self._build_url(XenditController._return_url)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.payment_request_notification_data
        ) as mock_req:
            tx._xendit_create_token_charge('pt-token123', 'card')
        self.assertEqual(mock_req.call_args.args[0], 'v3/payment_requests')
        self.assertEqual(mock_req.call_args.kwargs.get('api_version'), '2024-11-11')
        self.assertDictEqual(mock_req.call_args.kwargs.get('payload'), {
            'reference_id': tx.reference,
            'type': 'PAY',
            'country': tx.partner_id.country_id.code,
            'currency': 'IDR',
            'request_amount': 1000,
            'capture_method': 'AUTOMATIC',
            'payment_token_id': 'pt-token123',
            'channel_properties': {
                'card_on_file_type': 'CUSTOMER_UNSCHEDULED',
                'success_return_url': return_url,
                'failure_return_url': return_url,
            },
        })

    def test_token_charge_card_on_file_type_for_offline_operation(self):
        """ Test that offline (unattended) token charges are flagged as merchant-initiated
        rather than customer-initiated, to reduce the odds of a 3DS challenge. """
        tx = self._create_transaction('token', operation='offline')
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.payment_request_notification_data
        ) as mock_req:
            tx._xendit_create_token_charge('dummytoken', 'card')
            payload = mock_req.call_args.kwargs.get('payload')
            self.assertEqual(
                payload['channel_properties']['card_on_file_type'], 'MERCHANT_UNSCHEDULED'
            )

    def test_get_tx_from_notification_data_returns_tx(self):
        """ Test that the transaction is found based on the notification data. """
        tx = self._create_transaction('redirect')
        tx_found = self.env['payment.transaction']._get_tx_from_notification_data(
            'xendit', self.webhook_notification_data
        )
        self.assertEqual(tx, tx_found)

    def test_get_tx_from_notification_data_strips_suffixed_reference(self):
        """ Test that the transaction is found when Xendit appends a random suffix to the
        reference of the payment request created from the session. """
        tx = self._create_transaction('redirect')
        notification_data = dict(self.webhook_notification_data)
        notification_data['reference_id'] = f'{self.reference}_a1b2c3d4e5'
        tx_found = self.env['payment.transaction']._get_tx_from_notification_data(
            'xendit', notification_data
        )
        self.assertEqual(tx, tx_found)

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction('redirect')
        tx._process_notification_data(self.webhook_notification_data)
        self.assertEqual(tx.state, 'done')

    def test_processing_notification_data_pending_online_requires_action(self):
        """ Test that an online token charge requiring 3DS authentication is set to pending, so
        the customer can be redirected to complete the authentication. """
        tx = self._create_transaction('token')
        tx._process_notification_data(self.payment_request_requires_action_data)
        self.assertEqual(tx.state, 'pending')

    def test_processing_notification_data_fails_offline_requires_action(self):
        """ Test that an offline token charge requiring 3DS authentication is set to error
        instead of being left pending indefinitely, since there is no cardholder to redirect. """
        tx = self._create_transaction('token', operation='offline')
        tx._process_notification_data(self.payment_request_requires_action_data)
        self.assertEqual(tx.state, 'error')

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_processing_notification_data_tokenizes_transaction(self):
        """ Test that the transaction is tokenized when a token charge is successfully made on a
        transaction that saves payment details. """
        tx = self._create_transaction('redirect', tokenize=True)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.payment_request_notification_data
        ), patch(
            'odoo.addons.payment_xendit.models.payment_transaction.PaymentTransaction'
            '._xendit_tokenize_from_notification_data'
        ) as tokenize_mock:
            tx._xendit_create_token_charge('dummytoken', 'card')
            self.assertEqual(tokenize_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_xendit.controllers.main')
    def test_tokenization_flow_not_save_payment_details(self):
        """ Test that `_xendit_tokenize_from_notification_data` would not be triggered on a
        transaction that doesn't save the payment details. """
        tx = self._create_transaction('redirect')
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider.'
            '_xendit_make_request', return_value=self.payment_request_notification_data
        ), patch(
            'odoo.addons.payment_xendit.models.payment_transaction.PaymentTransaction.'
            '_xendit_tokenize_from_notification_data'
        ) as tokenize_check_mock:
            tx._xendit_create_token_charge('dummytoken', 'card')
            self.assertEqual(tokenize_check_mock.call_count, 0)

    def test_tokenize_from_notification_data_fetches_masked_card_number(self):
        """ Test that tokenizing fetches the payment token to get the masked card number, since
        it is not included in payment or payment request notifications. """
        tx = self._create_transaction('redirect', tokenize=True)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request', return_value=self.payment_token_data
        ) as mock_req:
            tx._xendit_tokenize_from_notification_data(self.payment_request_notification_data)
        self.assertEqual(
            mock_req.call_args.args[0], 'v3/payment_tokens/pt-6275md8ac5f00da60017cdc669'
        )
        self.assertEqual(mock_req.call_args.kwargs.get('method'), 'GET')
        self.assertEqual(mock_req.call_args.kwargs.get('api_version'), '2024-11-11')
        self.assertEqual(tx.token_id.payment_details, '2151')

    def test_tokenize_from_notification_data_skips_get_with_inline_card_details(self):
        """ Test that tokenizing doesn't fetch the payment token when the masked card number is
        already included in the notification data (e.g. from a `payment_token.activation`
        webhook notification). """
        tx = self._create_transaction('redirect', tokenize=True)
        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request'
        ) as mock_req:
            tx._xendit_tokenize_from_notification_data(self.token_activation_notification_data)
        self.assertEqual(mock_req.call_count, 0)
        self.assertEqual(tx.token_id.payment_details, '1000')
