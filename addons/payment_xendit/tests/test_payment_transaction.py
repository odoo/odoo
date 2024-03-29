# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_xendit.tests.common import XenditCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(PaymentHttpCommon, XenditCommon):

    def test_no_item_missing_from_invoice_request_payload(self):
        """ Test that the invoice request values are conform to the transaction fields. """
        self.maxDiff = 10000  # Allow comparing large dicts.
        tx = self._create_transaction(flow='redirect')
        request_payload = tx._xendit_prepare_invoice_request_payload()
        return_url = self._build_url('/payment/status')
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
            'success_redirect_url': return_url,
            'failure_redirect_url': return_url,
            'payment_methods': [self.payment_method_code.upper()],
            'currency': tx.currency_id.name,
        })

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
