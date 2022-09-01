# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_razorpay.tests.common import RazorpayCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(RazorpayCommon):

    def test_no_item_missing_from_order_request_payload(self):
        """ Test that the request values are conform to the transaction fields. """
        tx = self._create_transaction('redirect')
        request_payload = tx._razorpay_prepare_order_request_payload()
        self.maxDiff = 10000  # Allow comparing large dicts.
        converted_amount = payment_utils.to_minor_currency_units(tx.amount, tx.currency_id)
        self.assertDictEqual(request_payload, {
            'amount': converted_amount,
            'currency': tx.currency_id.name,
        })

    def test_void_is_not_supported(self):
        """ Test that trying to void an authorized transaction raises an error. """
        tx = self._create_transaction('redirect', state='authorized')
        self.assertRaises(UserError, func=tx._send_void_request)

    def test_get_tx_from_notification_data_returns_refund_tx(self):
        """ Test that the refund transaction is returned if it exists when processing refund
        notification data. """
        refund_tx = self._create_transaction('redirect')
        returned_tx = self.env['payment.transaction']._get_tx_from_notification_data(
            'razorpay', dict(self.refund_data, **{
                'entity_type': 'refund',
                'notes': {
                    'reference': refund_tx.reference,
                },
            })
        )
        self.assertEqual(returned_tx, refund_tx)

    def test_get_tx_from_notification_data_creates_refund_tx_when_missing(self):
        """ Test that a refund transaction is created when processing refund notification data
        without reference. """
        source_tx = self._create_transaction(
            'redirect', state='done', acquirer_reference=self.payment_id
        )
        refund_tx = self.env['payment.transaction']._get_tx_from_notification_data(
            'razorpay', dict(self.refund_data, entity_type='refund')
        )
        self.assertTrue(
            refund_tx,
            msg="If no refund tx is found with the refund data, a refund tx should be created.",
        )
        self.assertNotEqual(refund_tx, source_tx)
        self.assertEqual(refund_tx.source_transaction_id, source_tx)

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction('redirect')
        with patch(
            'odoo.addons.payment_razorpay.models.payment_acquirer.PaymentAcquirer'
            '._razorpay_make_request', return_value=self.payment_data
        ):
            tx._process_notification_data(self.payment_data)
        self.assertEqual(tx.state, 'done')
