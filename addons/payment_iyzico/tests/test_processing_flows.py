# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_iyzico.controllers.main import IyzicoController
from odoo.addons.payment_iyzico.tests.common import IyzicoCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(IyzicoCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_iyzico.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """ Test that receiving a redirect notification triggers the processing of the notification
        data. """
        self._create_transaction('redirect', provider_reference='dummy_token')
        url = self._build_url(IyzicoController._return_url)
        with patch(
            'odoo.addons.payment_iyzico.models.payment_provider.PaymentProvider'
            '._iyzico_make_request', return_value=self.notification_data
        ), patch(
            'odoo.addons.payment_iyzico.models.payment_provider.PaymentProvider'
            '._iyzico_calculate_signature', return_value=self.signature
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_http_post_request(url, data=self.return_data)
        self.assertEqual(handle_notification_data_mock.call_count, 1)
