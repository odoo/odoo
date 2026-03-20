# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug import urls

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_nuvei.controllers.main import NuveiController
from odoo.addons.payment_nuvei.tests.common import NuveiCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(NuveiCommon):

    def test_no_item_missing_from_rendering_values(self):
        """ Test that the rendering values match what we expect. """
        def make_uuid():
            return "0000-0000-0000-0000"

        tx = self._create_transaction(flow='redirect')
        return_url = self._build_url(NuveiController._return_url)
        webhook_url = self._build_url(NuveiController._webhook_url)
        cancel_url_params = {
            'tx_ref': tx.reference,
            'error_access_token': self._generate_test_access_token(tx.reference),
        }
        cancel_url = f'{return_url}?{urls.url_encode(cancel_url_params)}'
        first_name, last_name = " ".join(tx.partner_name.split()[:-1]), tx.partner_name.split()[-1]
        expected_values = {
            'api_url': 'https://ppp-test.safecharge.com/ppp/purchase.do',
            'url_params': {
                'address1': tx.partner_address,
                'city': tx.partner_city,
                'country': tx.partner_country_id.code,
                'currency': tx.currency_id.name,
                'email': tx.partner_email,
                'encoding': 'UTF-8',
                'first_name': first_name,
                'item_amount_1': tx.amount,
                'item_name_1': tx.reference,
                'item_quantity_1': 1,
                'invoice_id': tx.reference,
                'last_name': last_name,
                'merchantLocale': tx.partner_lang,
                'merchant_id': self.provider.nuvei_merchant_identifier,
                'merchant_site_id': self.provider.nuvei_site_identifier,
                'payment_method_mode': 'filter',
                'payment_method': 'unknown',
                'phone1': '+3212345678',
                'state': tx.partner_state_id.code or '',
                'user_token_id': make_uuid(),
                'time_stamp': tx.create_date.strftime('%Y-%m-%d.%H:%M:%S'),
                'total_amount': self.amount,
                'version': '4.0.0',
                'zip': tx.partner_zip,
                'back_url': cancel_url,
                'error_url': cancel_url,
                'notify_url': webhook_url,
                'pending_url': return_url,
                'success_url': return_url,
            }
        }
        checksum = self.provider._nuvei_calculate_signature(
            expected_values['url_params'], incoming=False
        )
        expected_values['checksum'] = checksum

        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ), patch('odoo.addons.payment_nuvei.models.payment_transaction.uuid4', make_uuid):
            processing_values = tx._get_specific_rendering_values(None)
        self.assertDictEqual(processing_values, expected_values)

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that no key is omitted from the rendering values. """
        tx = self._create_transaction(flow='redirect')
        expected_input_keys = [
            'checksum',
            'address1',
            'city',
            'country',
            'currency',
            'email',
            'encoding',
            'first_name',
            'item_amount_1',
            'item_name_1',
            'item_quantity_1',
            'invoice_id',
            'last_name',
            'merchantLocale',
            'merchant_id',
            'merchant_site_id',
            'payment_method_mode',
            'payment_method',
            'phone1',
            'state',
            'time_stamp',
            'user_token_id',
            'total_amount',
            'version',
            'zip',
            'notify_url',
            'success_url',
            'error_url',
            'pending_url',
            'back_url',
        ]
        expected_input_keys.sort()
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            processing_values = tx._get_processing_values()

        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], 'https://ppp-test.safecharge.com/ppp/purchase.do')
        self.assertEqual(form_info['method'], 'post')
        input_keys = list(form_info['inputs'].keys())
        input_keys.sort()
        self.assertListEqual(input_keys, expected_input_keys)

    def test_apply_updates_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the payment data indicates a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        tx._apply_updates(self.payment_data)
        self.assertEqual(tx.state, 'done')

    def test_apply_updates_sets_transaction_in_error(self):
        """ Test that the transaction state is set to 'error' when the payment data indicates
        that something went wrong. """
        tx = self._create_transaction(flow='redirect')
        payload = dict(self.payment_data, Status='ERROR', Reason='Invalid Card')
        tx._apply_updates(payload)
        self.assertEqual(tx.state, 'error')

    def test_apply_updates_sets_unknown_transaction_in_error(self):
        """ Test that the transaction state is set to 'error' when the payment data returns
        something with an unknown state. """
        tx = self._create_transaction(flow='redirect')
        payload = dict(self.payment_data, Status='???', Reason='Invalid Card')
        tx._apply_updates(payload)
        self.assertEqual(tx.state, 'error')

    def test_processing_payment_data_sets_transaction_to_cancel(self):
        """ Test that the transaction state is set to 'cancel' when the payment data is
        missing. """
        tx = self._create_transaction(flow='redirect')
        tx._apply_updates({})
        self.assertEqual(tx.state_message, 'The customer left the payment page.')
        self.assertEqual(tx.state, 'cancel')

    def test_processing_values_contain_rounded_amount_usd_webpay(self):
        """ Ensure that for USD currency with Webpay payment method, processing_values should
        contain a value which is the amount rounded down to the nearest 0. """
        currency_usd = self.env.ref('base.USD')
        webpay_id = self.env.ref('payment.payment_method_webpay')
        tx = self._create_transaction(
            'redirect', amount=1000.50, currency_id=currency_usd.id, payment_method_id=webpay_id.id
        )
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            processing_values = tx._get_specific_rendering_values(None)
        self.assertEqual(processing_values.get('url_params').get('total_amount'), 1000)
