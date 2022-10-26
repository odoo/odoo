# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_flutterwave.tests.common import FlutterwaveCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(FlutterwaveCommon):

    def test_no_item_missing_from_rendering_values(self):
        """ Test that the rendered values are conform to the transaction fields. """
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_flutterwave.models.payment_provider.PaymentProvider'
            '._flutterwave_make_request', return_value={'data': {'link': 'https://dummy.com'}}
        ):
            rendering_values = tx._get_specific_rendering_values(None)
        self.assertDictEqual(rendering_values, {'api_url': 'https://dummy.com'})

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that the `api_url` key is not omitted from the rendering values. """
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_flutterwave.models.payment_transaction.PaymentTransaction'
            '._get_specific_rendering_values', return_value={'api_url': 'https://dummy.com'}
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], 'https://dummy.com')
        self.assertEqual(form_info['method'], 'get')
        self.assertDictEqual(form_info['inputs'], {})

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_flutterwave.models.payment_provider.PaymentProvider'
            '._flutterwave_make_request', return_value=self.verification_data
        ):
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tx.state, 'done')

    def test_processing_notification_data_tokenizes_transaction(self):
        """ Test that the transaction is tokenized when it was requested and the notification data
        include token data. """
        tx = self._create_transaction(flow='redirect', tokenize=True)
        with patch(
            'odoo.addons.payment_flutterwave.models.payment_provider.PaymentProvider'
            '._flutterwave_make_request', return_value=self.verification_data
        ), patch(
            'odoo.addons.payment_flutterwave.models.payment_transaction.PaymentTransaction'
            '._flutterwave_tokenize_from_notification_data'
        ) as tokenize_mock:
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tokenize_mock.call_count, 1)
