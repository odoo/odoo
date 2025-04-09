# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment_dpo.tests.common import DPOCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(DPOCommon):

    def test_no_item_missing_from_rendering_values(self):
        """ Test that the rendered values are conform to the transaction fields. """
        tx = self._create_transaction(flow='redirect')
        transaction_token = "dummy_token"
        expected_values = {
            'api_url': f'https://secure.3gdirectpay.com/payv2.php?ID={transaction_token}',
        }
        with patch(
            'odoo.addons.payment_dpo.models.payment_transaction.PaymentTransaction'
            '._dpo_create_token', return_value='dummy_token'
        ):
            self.assertEqual(tx._get_specific_rendering_values(None), expected_values)

    def test_get_tx_from_notification_data_returns_tx(self):
        """ Test that the transaction is returned from the notification data. """
        tx = self._create_transaction(flow='redirect')
        tx_found = self.env['payment.transaction']._get_tx_from_notification_data(
            'dpo', self.notification_data
        )
        self.assertEqual(tx, tx_found)

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        tx._process_notification_data(self.notification_data)
        self.assertEqual(tx.state, 'done')
