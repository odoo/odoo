# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_bictorys.controllers.main import BictorysController
from odoo.addons.payment_bictorys.tests.common import BictorysCommon


@tagged('post_install', '-at_install')
class BictorysTest(BictorysCommon, PaymentHttpCommon):

    def test_rendering_values_contain_redirect_url(self):
        """ Test that the rendering values include the Bictorys redirect URL. """
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_bictorys.models.payment_provider.PaymentProvider'
            '._bictorys_make_request',
            return_value={
                'link': 'https://pay.bictorys.com/test',
                'chargeId': 'charge_123',
                'opToken': 'token_abc',
            },
        ):
            rendering_values = tx._get_specific_rendering_values({})
        self.assertEqual(rendering_values['api_url'], 'https://pay.bictorys.com/test')
        self.assertEqual(rendering_values['charge_id'], 'charge_123')

    def test_get_tx_from_notification_data_with_reference(self):
        """ Test that the transaction is correctly retrieved from notification data. """
        tx = self._create_transaction(flow='redirect')
        found_tx = self.env['payment.transaction']._get_tx_from_notification_data(
            'bictorys', self.notification_data
        )
        self.assertEqual(tx, found_tx)

    def test_get_tx_from_notification_data_missing_reference(self):
        """ Test that a ValidationError is raised when the reference is missing. """
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._get_tx_from_notification_data(
                'bictorys', {}
            )

    def test_process_notification_data_done(self):
        """ Test that a successful notification sets the transaction as done. """
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_bictorys.models.payment_provider.PaymentProvider'
            '._bictorys_make_request',
            return_value={'data': {'id': 'bictorys_tx_123', 'status': 'successful'}},
        ):
            tx._process_notification_data(self.notification_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, 'bictorys_tx_123')

    def test_process_notification_data_cancel(self):
        """ Test that a cancel status sets the transaction as cancelled. """
        tx = self._create_transaction(flow='redirect')
        tx._process_notification_data({'status': 'cancel', 'paymentReference': self.reference})
        self.assertEqual(tx.state, 'cancel')

    def test_webhook_returns_empty_response(self):
        """ Test that the webhook acknowledges with an empty response. """
        tx = self._create_transaction(flow='redirect')
        url = self._build_url(BictorysController._webhook_url)
        with patch(
            'odoo.addons.payment_bictorys.controllers.main.BictorysController'
            '._verify_notification_signature'
        ), patch(
            'odoo.addons.payment_bictorys.models.payment_provider.PaymentProvider'
            '._bictorys_make_request',
            return_value={'data': {'id': 'bictorys_tx_123', 'status': 'successful'}},
        ):
            response = self._make_http_post_request(
                url, data=self.notification_data
            )
        self.assertEqual(response.status_code, 200)
