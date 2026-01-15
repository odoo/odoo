# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paymob.controllers.main import PaymobController
from odoo.addons.payment_paymob.tests.common import PaymobCommon


@tagged('post_install', '-at_install')
class PaymobTest(PaymobCommon, PaymentHttpCommon):

    def test_no_item_missing_from_rendering_values(self):
        """ Test that when the redirect flow is triggered, rendering_values contains the API_URL and
        URL_PARAMS corresponding to the response of API request. """
        tx = self._create_transaction('redirect')
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value={'client_secret': 'dummy_secret'},
        ):
            rendering_values = tx._get_specific_rendering_values(None)
        paymob_url = self.paymob._paymob_get_api_url()
        paymob_pk = self.paymob.paymob_public_key
        self.assertEqual(rendering_values['api_url'], f'{paymob_url}/unifiedcheckout/')
        self.assertEqual(rendering_values['url_params']['publicKey'], paymob_pk)
        self.assertEqual(rendering_values['url_params']['clientSecret'], 'dummy_secret')

    def test_paymob_return_data(self):
        """ Test the processing of the paymob return data. """
        tx = self._create_transaction('redirect')
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value={'id': 'dummy_id'}
        ):
            tx._get_specific_rendering_values(None)  # Set provider reference here
            self.assertEqual(tx.provider_reference, self.redirection_data['id'])
            self.assertEqual(tx.state, 'draft')
            tx._process('paymob', self.redirection_data)
            self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_paymob.controllers.main')
    def test_compute_signature(self):
        """ Test the computation of the signature sent by paymob """
        computed_hmac = PaymobController._compute_signature(
            self.redirection_data, self.provider.paymob_hmac_key
        )
        self.assertEqual(computed_hmac, self.hmac_signature)

    @mute_logger('odoo.addons.payment_paymob.controllers.main')
    def test_normalize_webhook_data(self):
        """ Test the normalization of the paymob webhook data """
        normalized_data = PaymobController._normalize_response(
            self.webhook_data, self.hmac_signature
        )
        self.assertDictEqual(normalized_data, self.redirection_data)

    def test_change_paymob_account_country(self):
        """ Test that changing the Paymob account country will change the currency accordingly. """
        self.provider.paymob_account_country_id = self.quick_ref('base.sa')
        self.assertEqual(self.provider.available_currency_ids.name, 'SAR')
