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
            'external_reference': tx.reference,
            'notification_url': f'{webhook_url}/{sanitized_reference}',
            'statement_descriptor': tx.company_id.name,
            'auto_return': 'all',
            'back_urls': {
                'failure': return_url,
                'pending': return_url,
                'success': return_url,
            },
            'items': [{
                'currency_id': tx.currency_id.name,
                'quantity': 1,
                'title': tx.reference,
                'unit_price': tx.amount,
            }],
            'payer': {
                'name': tx.partner_name,
                'email': tx.partner_email,
                'phone': {'number': tx.partner_phone},
                'address': {'street_name': tx.partner_address, 'zip_code': tx.partner_zip},
            },
        })

    def test_tokenizing_payment_is_first_credential_on_file(self):
        tx = self._create_transaction(flow='direct', tokenize=True)
        payload = tx._mercado_pago_prepare_payment_request_payload()
        self.assertDictEqual(payload['point_of_interaction'], {
            'type': 'CREDENTIAL_ON_FILE',
            'sub_type': 'unscheduled',
            'transaction_data': {
                'first_transaction': True,
                'storage': 'store',
                'transaction_initiator': 'customer',
            },
        })

    def test_token_payment_references_first_payment(self):
        token = self._create_token()
        tx = self._create_transaction(
            flow='token', reference='renewal', operation='offline', token_id=token.id,
        )
        self.assertIsNone(tx._mercado_pago_prepare_cof_payload())

        self._create_transaction(
            flow='direct', token_id=token.id, provider_reference=self.MP_PAYMENT_ID,
        )
        self._create_transaction(
            flow='token', reference='later', token_id=token.id, provider_reference='999',
        )
        self.assertDictEqual(tx._mercado_pago_prepare_cof_payload()['transaction_data'], {
            'first_transaction': False,
            'storage': 'stored',
            'transaction_initiator': 'merchant',
            'reference': {'id': self.MP_PAYMENT_ID},
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

    def test_apply_updates_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        tx._apply_updates(self.verification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_mercado_pago.models.payment_transaction')
    def test_apply_updates_rejects_transaction(self):
        """ Test that the transaction state is set to 'error' when the payment data indicate a status of
        404 error payment. """
        tx = self._create_transaction(flow='redirect')
        tx._apply_updates(self.verification_data_for_error_state)
        self.assertEqual(tx.state, 'error')

    def test_cop_currency_rounding(self):
        """Ensure COP payments get sent as integer amounts to Mercado Pago."""
        self.currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', 'COP')],
            limit=1,
        )
        self.amount = 999.99
        tx = self._create_transaction(flow='redirect')
        request_payload = tx._mercado_pago_prepare_preference_request_payload()
        self.assertEqual(
            request_payload['items'][0]['unit_price'],
            999,
            "COP payment amounts should be rounded down in the payload sent to Mercado Pago",
        )
