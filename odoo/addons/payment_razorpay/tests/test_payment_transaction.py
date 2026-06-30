# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from datetime import datetime
from dateutil.relativedelta import relativedelta

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_razorpay.tests.common import RazorpayCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(RazorpayCommon):

    def test_no_item_missing_from_order_request_payload(self):
        """ Test that the request values are conform to the transaction fields. """
        tx = self._create_transaction('redirect', operation='online_direct')
        request_payload = tx._razorpay_prepare_order_payload(customer_id=self.razorpay_customer_id)
        self.maxDiff = 10000  # Allow comparing large dicts.
        converted_amount = payment_utils.to_minor_currency_units(tx.amount, tx.currency_id)
        self.assertDictEqual(request_payload, {
            'amount': converted_amount,
            'currency': tx.currency_id.name,
            'customer_id': self.razorpay_customer_id,
            'method': 'card',
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
            'redirect', state='done', provider_reference=self.payment_id
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
            'odoo.addons.payment_razorpay.models.payment_provider.PaymentProvider'
            '._razorpay_make_request', return_value=self.payment_data
        ):
            tx._process_notification_data(self.payment_data)
        self.assertEqual(tx.state, 'done')

    def test_order_request_payload_for_tokenize_tx(self):
        """ Test that order payload for tokenize tx is proper. """
        tx = self._create_transaction('redirect', operation='online_direct', tokenize=True)
        self.assertDictEqual(
            tx._get_specific_rendering_values(None),
            {},
            msg="Should return empty dict of rendering values for tokenize transaction",
        )

        request_payload = tx._razorpay_prepare_order_payload(customer_id=self.razorpay_customer_id)
        converted_amount = payment_utils.to_minor_currency_units(tx.amount, tx.currency_id)
        token_expiry_date = datetime.today() + relativedelta(years=10)
        token_expiry_timestamp = time.mktime(token_expiry_date.timetuple())
        self.assertDictEqual(request_payload, {
            'token': {
                "expire_at": token_expiry_timestamp,
                "frequency": "as_presented",
                'max_amount': 100000000,
            },
            'amount': converted_amount,
            'currency': tx.currency_id.name,
            'customer_id': self.razorpay_customer_id,
            'method': 'card',
        })

    def test_processing_notification_data_confirms_tokenize_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction('redirect', tokenize=True)
        tx._process_notification_data(self.tokenize_payment_data)
        self.assertEqual(tx.state, 'done')

    def test_processing_notification_data_only_tokenizes_once(self):
        """ Test that only one token is created when notification data of a given transaction are
        processed multiple times. """
        tx1 = self._create_transaction('redirect', reference='tx1', tokenize=True)
        tx1._process_notification_data(self.tokenize_payment_data)
        with patch(
            'odoo.addons.payment_razorpay.models.payment_transaction.PaymentTransaction'
            '._razorpay_tokenize_from_notification_data'
        ) as tokenize_mock:
            # Create the second transaction with the first transaction's token.
            tx2 = self._create_transaction('token', reference='tx2', token_id=tx1.token_id.id)
            tx2._process_notification_data(self.tokenize_payment_data)
            self.assertEqual(
                tokenize_mock.call_count,
                0,
                msg="No new token should be created for transactions already linked to a token.",
            )

    def test_token_creation_for_tokenize_transaction(self):
        """ Test that the token is created on confirmation of transactions to tokenize. """
        tx = self._create_transaction(
            'redirect', tokenize=True, payment_method_id=self.payment_method_id
        )
        tx._process_notification_data(self.tokenize_payment_data)
        token = tx.token_id
        self.assertTrue(token, msg="A token should be created for transactions to tokenize.")
        self.assertFalse(
            tx.tokenize,
            msg="The transaction should no longer require tokenization after the token creation.",
        )
        self.assertEqual(
            token.provider_ref,
            f'{self.tokenize_payment_data["customer_id"]},{self.tokenize_payment_data["token_id"]}',
            msg="The provider_ref is wrongly computed.",
        )
