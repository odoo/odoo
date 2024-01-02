# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from urllib.parse import quote as url_quote

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(MercadoPagoCommon, PaymentHttpCommon):

    def test_no_item_missing_from_preference_request_payload(self):
        """ Test that the request values are conform to the transaction fields. """
        tx = self._create_transaction(flow='redirect')
        request_payload = tx._mercado_pago_prepare_preference_request_payload()
        self.maxDiff = 10000  # Allow comparing large dicts.
        return_url = self._build_url('/payment/mercado_pago/return')
        webhook_url = self._build_url('/payment/mercado_pago/webhook')
        sanitized_reference = url_quote(tx.reference)
        self.assertDictEqual(request_payload, {
            'auto_return': 'all',
            'back_urls': {
                'failure': return_url,
                'pending': return_url,
                'success': return_url,
            },
            'external_reference': tx.reference,
            'items': [{
                'currency_id': tx.currency_id.name,
                'quantity': 1,
                'title': tx.reference,
                'unit_price': tx.amount,
            }],
            'notification_url': f'{webhook_url}/{sanitized_reference}',
            'payer': {
                'address': {'street_name': tx.partner_address, 'zip_code': tx.partner_zip},
                'email': tx.partner_email,
                'name': tx.partner_name,
                'phone': {'number': tx.partner_phone},
            },
            'payment_methods': {'installments': 1},
        })

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that the `api_url` key is not omitted from the rendering values. """
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_mercado_pago.models.payment_transaction.PaymentTransaction'
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
            'odoo.addons.payment_mercado_pago.models.payment_provider.PaymentProvider'
            '._mercado_pago_make_request', return_value=self.verification_data
        ):
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tx.state, 'done')
