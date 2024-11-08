# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

# from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_dpo.controllers.main import DPOController
from odoo.addons.payment_dpo.tests.common import DPOCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(DPOCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_dpo.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """ Test that receiving a valid redirect notification triggers the processing of the
        notification data. """
        self._create_transaction('redirect')
        url = self._build_url(DPOController._return_url)
        with patch(
            'odoo.addons.payment_dpo.controllers.main.DPOController'
            '._dpo_verify_transaction_token'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_http_get_request(url, params=self.notification_data)
            self.assertEqual(handle_notification_data_mock.call_count, 1)
