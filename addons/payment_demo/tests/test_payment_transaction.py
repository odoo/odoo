# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_demo.tests.common import PaymentDemoCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged('-at_install', 'post_install')
class TestPaymentTransaction(PaymentDemoCommon, PaymentHttpCommon):

    def test_processing_notification_data_sets_transaction_pending(self):
        """ Test that the transaction state is set to 'pending' when the notification data indicate
        a pending payment. """
        tx = self._create_transaction('direct')
        tx._process_notification_data(dict(self.notification_data, simulated_state='pending'))
        self.assertEqual(tx.state, 'pending')

    def test_processing_notification_data_authorizes_transaction(self):
        """ Test that the transaction state is set to 'authorize' when the notification data
        indicate a successful payment and manual capture is enabled. """
        self.provider.capture_manually = True
        tx = self._create_transaction('direct')
        tx._process_notification_data(self.notification_data)
        self.assertEqual(tx.state, 'authorized')

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction('direct')
        tx._process_notification_data(self.notification_data)
        self.assertEqual(tx.state, 'done')

    def test_processing_notification_data_cancels_transaction(self):
        """ Test that the transaction state is set to 'cancel' when the notification data indicate
        an unsuccessful payment. """
        tx = self._create_transaction('direct')
        tx._process_notification_data(dict(self.notification_data, simulated_state='cancel'))
        self.assertEqual(tx.state, 'cancel')

    def test_processing_notification_data_sets_transaction_in_error(self):
        """ Test that the transaction state is set to 'error' when the notification data indicate
        an error during the payment. """
        tx = self._create_transaction('direct')
        tx._process_notification_data(dict(self.notification_data, simulated_state='error'))
        self.assertEqual(tx.state, 'error')

    def test_processing_notification_data_tokenizes_transaction(self):
        """ Test that the transaction is tokenized when it was requested and the notification data
        include token data. """
        tx = self._create_transaction('direct', tokenize=True)
        with patch(
            'odoo.addons.payment_demo.models.payment_transaction.PaymentTransaction'
            '._demo_tokenize_from_notification_data'
        ) as tokenize_mock:
            tx._process_notification_data(self.notification_data)
        self.assertEqual(tokenize_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_demo.models.payment_transaction')
    def test_processing_notification_data_propagates_simulated_state_to_token(self):
        """ Test that the simulated state of the notification data is set on the token when
        processing notification data. """
        for counter, state in enumerate(['pending', 'done', 'cancel', 'error']):
            tx = self._create_transaction(
                'direct', reference=f'{self.reference}-{counter}', tokenize=True
            )
            tx._process_notification_data(dict(self.notification_data, simulated_state=state))
            self.assertEqual(tx.token_id.demo_simulated_state, state)

    def test_making_a_payment_request_propagates_token_simulated_state_to_transaction(self):
        """ Test that the simulated state of the token is set on the transaction when making a
        payment request. """
        for counter, state in enumerate(['pending', 'done', 'cancel', 'error']):
            tx = self._create_transaction(
                'direct', reference=f'{self.reference}-{counter}'
            )
            tx.token_id = self._create_token(demo_simulated_state=state)
            tx._send_payment_request()
            self.assertEqual(tx.state, tx.token_id.demo_simulated_state)
