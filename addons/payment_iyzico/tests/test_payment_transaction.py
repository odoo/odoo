# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_iyzico.tests.common import IyzicoCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(IyzicoCommon, PaymentHttpCommon):

    def test_no_item_missing_from_checkoutform_initialize_payload(self):
        """ Test that the request values are conform to the transaction fields. """
        tx = self._create_transaction(flow='redirect')
        request_payload = tx._iyzico_prepare_checkoutform_initialize_payload()
        first_name, last_name = payment_utils.split_partner_name(tx.partner_name)
        return_url = self._build_url('/payment/iyzico/return')
        self.assertDictEqual(request_payload, {
            'basketId': tx.reference,
            'basketItems': [{
                'id': 'Dummy ItemID',
                'price': tx.amount,
                'name': 'Dummy Product',
                'category1': 'Dummy Category',
                'itemType': "VIRTUAL",
            }],
            'billingAddress': {
                'address': tx.partner_address,
                'contactName': tx.partner_name,
                'city': tx.partner_city,
                'country': tx.partner_country_id.name,
            },
            'buyer': {
                'id': tx.id,
                'name': first_name,
                'surname': last_name,
                'identityNumber': f'{first_name}_{tx.partner_id.id}',
                'email': tx.partner_email,
                'registrationAddress': tx.partner_address,
                'city': tx.partner_city,
                'country': tx.partner_country_id.name,
                'ip': tx.id,
            },
            'callbackUrl': return_url,
            'conversationId': tx.reference,
            'currency': tx.currency_id.name,
            'locale': tx.env.lang == 'tr_TR' and 'tr' or 'en',
            "paidPrice": tx.amount,
            'price': tx.amount,
        })

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that the `api_url` key is not omitted from the rendering values. """
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_iyzico.models.payment_transaction.PaymentTransaction'
            '._get_specific_rendering_values', return_value={'api_url': 'https://dummy.com'}
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], 'https://dummy.com')
        self.assertEqual(form_info['method'], 'get')
        self.assertDictEqual(form_info['inputs'], {})

    def test_get_tx_from_notification_data_returns_tx(self):
        """ Test that the transaction is returned from the notification data. """
        tx = self._create_transaction(flow='redirect', provider_reference='dummy_token')
        tx_found = self.env['payment.transaction']._get_tx_from_notification_data(
            'iyzico', self.notification_data
        )
        self.assertEqual(tx, tx_found)

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        tx._process_notification_data(self.notification_data)
        self.assertEqual(tx.state, 'done')
