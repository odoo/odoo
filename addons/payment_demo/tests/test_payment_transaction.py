# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_demo.tests.common import PaymentDemoCommon


@tagged('-at_install', 'post_install')
class TestPaymentTransaction(PaymentDemoCommon, PaymentHttpCommon):

    def test_apply_updates_sets_transaction_pending(self):
        """ Test that the transaction state is set to 'pending' when the payment data indicate
        a pending payment. """
        tx = self._create_transaction('direct')
        tx._apply_updates(dict(self.payment_data, simulated_state='pending'))
        self.assertEqual(tx.state, 'pending')

    def test_apply_updates_authorizes_transaction(self):
        """ Test that the transaction state is set to 'authorize' when the payment data
        indicate a successful payment and manual capture is enabled. """
        self.provider.capture_manually = True
        tx = self._create_transaction('direct')
        tx._apply_updates(self.payment_data)
        self.assertEqual(tx.state, 'authorized')

    def test_apply_updates_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment. """
        tx = self._create_transaction('direct')
        tx._apply_updates(self.payment_data)
        self.assertEqual(tx.state, 'done')

    def test_apply_updates_cancels_transaction(self):
        """ Test that the transaction state is set to 'cancel' when the payment data indicate
        an unsuccessful payment. """
        tx = self._create_transaction('direct')
        tx._apply_updates(dict(self.payment_data, simulated_state='cancel'))
        self.assertEqual(tx.state, 'cancel')

    def test_apply_updates_sets_transaction_in_error(self):
        """ Test that the transaction state is set to 'error' when the payment data indicate
        an error during the payment. """
        tx = self._create_transaction('direct')
        tx._apply_updates(dict(self.payment_data, simulated_state='error'))
        self.assertEqual(tx.state, 'error')

    def test_apply_updates_tokenizes_transaction(self):
        """ Test that the transaction is tokenized when it was requested and the payment data
        include token data. """
        tx = self._create_transaction('direct', tokenize=True)
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._tokenize'
        ) as tokenize_mock:
            tx._apply_updates(self.payment_data)
        self.assertEqual(tokenize_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_demo.models.payment_transaction')
    def test_apply_updates_propagates_simulated_state_to_token(self):
        """ Test that the simulated state of the payment data is set on the token when
        processing payment data. """
        for counter, state in enumerate(['pending', 'done', 'cancel', 'error']):
            tx = self._create_transaction(
                'direct', reference=f'{self.reference}-{counter}', tokenize=True
            )
            tx._apply_updates(dict(self.payment_data, simulated_state=state))
            self.assertEqual(tx.token_id.demo_simulated_state, state)

    def test_making_a_payment_request_propagates_token_simulated_state_to_transaction(self):
        """ Test that the simulated state of the token is set on the transaction when making a
        payment request. """
        for counter, state in enumerate(['pending', 'done', 'cancel', 'error']):
            tx = self._create_transaction(
                'direct', reference=f'{self.reference}-{counter}'
            )
            tx.token_id = self._create_token(demo_simulated_state=state)
            tx._charge_with_token()
            self.assertEqual(tx.state, tx.token_id.demo_simulated_state)
