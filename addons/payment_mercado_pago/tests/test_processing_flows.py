# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(MercadoPagoCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_mercado_pago.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """ Test that receiving a redirect notification triggers the processing of the notification
        data. """
        self._create_transaction(flow='redirect')
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value=self.verification_data,
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_http_get_request(url, params=self.redirect_payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_mercado_pago.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """ Test that receiving a valid webhook notification triggers the processing of the
        payment data. """
        tx = self._create_transaction(flow='redirect')
        url = self._build_url(f'{const.WEBHOOK_ROUTE}/{tx.reference}')
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value=self.verification_data,
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_mercado_pago.controllers.payment')
    def test_redirect_notification_redirects_when_payment_data_unavailable(self):
        """ Test that the customer is redirected to the status page when the payment data cannot
        be fetched from Mercado Pago. """
        self._create_transaction(flow='redirect')
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            side_effect=ValidationError("Service Unavailable"),
        ):
            response = self._make_http_get_request(url, params=self.redirect_payment_data)
        self.assertTrue(response.url.endswith('/payment/status'))

    @mute_logger('odoo.addons.payment_mercado_pago.controllers.payment')
    def test_webhook_notification_is_rejected_when_payment_data_unavailable(self):
        """ Test that the webhook notification is not acknowledged when the payment data cannot be
        fetched from Mercado Pago, so that Mercado Pago sends it again later. """
        tx = self._create_transaction(flow='redirect')
        url = self._build_url(f'{const.WEBHOOK_ROUTE}/{tx.reference}')
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            side_effect=ValidationError("Service Unavailable"),
        ):
            response = self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(response.status_code, 503)

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_webhook_notification_for_unknown_reference_is_acknowledged(self):
        """ Test that the webhook notification of an unknown transaction is acknowledged. """
        url = self._build_url(f'{const.WEBHOOK_ROUTE}/unknown-reference')
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
        ) as send_api_request_mock:
            response = self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(send_api_request_mock.call_count, 0)
