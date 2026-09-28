# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mollie.controllers.main import MollieController
from odoo.addons.payment_mollie.tests.common import MollieCommon


@tagged('post_install', '-at_install')
class MollieTest(MollieCommon, PaymentHttpCommon):

    def test_payment_request_payload_values(self):
        tx = self._create_transaction(flow='redirect')

        payload = tx._mollie_prepare_payment_request_payload()

        self.assertDictEqual(payload['amount'], {'currency': 'EUR', 'value': '1111.11'})
        self.assertEqual(payload['description'], tx.reference)

    @mute_logger(
        'odoo.addons.payment_mollie.controllers.main',
        'odoo.addons.payment_mollie.models.payment_transaction',
    )
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(MollieController._webhook_url)
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value={
                'status': 'paid',
                'amount': {'value': str(self.amount), 'currency': self.currency.name},
            },
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_return_from_checkout_redirects_when_payment_data_unavailable(self):
        self._create_transaction("redirect")
        url = self._build_url(MollieController._return_url)
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            side_effect=ValidationError("Service Unavailable"),
        ):
            response = self._make_http_get_request(url, params=self.payment_data)
        self.assertTrue(response.url.endswith('/payment/status'))

    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_webhook_notification_is_rejected_when_payment_data_unavailable(self):
        self._create_transaction("redirect")
        url = self._build_url(MollieController._webhook_url)
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            side_effect=ValidationError("Service Unavailable"),
        ):
            response = self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(response.status_code, 503)
