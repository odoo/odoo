# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

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
