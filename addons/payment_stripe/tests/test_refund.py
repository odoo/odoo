# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.tests.common import StripeCommon


@tagged('post_install', '-at_install')
class StripeTestRefund(StripeCommon, PaymentHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.full_refund_response = {
            'amount': 111111,
            'charge': 'ch_000000000000000000000000',
            'currency': 'eur',
            'id': 're_000000000000000000000000',
            'metadata': {'reference': 'R-Test Transaction'},
            'object': 'refund',
            'payment_intent': 'pi_000000000000000000000000',
            'status': 'succeeded',
        }

        cls.pending_refund_response = {
            'amount': 111111,
            'charge': 'ch_000000000000000000000000',
            'currency': 'eur',
            'id': 're_000000000000000000000000',
            'metadata': {'reference': 'R-Test Transaction'},
            'object': 'refund',
            'payment_intent': 'pi_000000000000000000000000',
            'status': 'pending',
        }

        cls.pending_refund_notification_data = {
            'id': 'evt_000000000000000000000000',
            'object': 'event',
            'api_version': '2019-05-16',
            'created': 1646325147,
            'data': {
                'object': {
                    'id': 're_000000000000000000000000',
                    'object': 'refund',
                    'amount': 111111,
                    'charge': 'ch_000000000000000000000000',
                    'created': 1646325025,
                    'currency': 'eur',
                    'metadata': {
                        'reference': 'R-Test Transaction'
                    },
                    'payment_intent': 'pi_000000000000000000000000',
                    'status': 'succeeded',
                },
                'previous_attributes': {
                    'status': 'pending'
                }
            },
            'livemode': False,
            'pending_webhooks': 1,
            'type': 'charge.refund.updated'
        }

        cls.error_refund_notification_data = {
            'id': 'evt_000000000000000000000000',
            'object': 'event',
            'api_version': '2019-05-16',
            'created': 1646325822,
            'data': {
                'object': {
                    'id': 're_000000000000000000000000',
                    'object': 'refund',
                    'amount': 111111,
                    'charge': 'ch_000000000000000000000000',
                    'created': 1646325821,
                    'currency': 'eur',
                    'failure_balance_transaction': 'txn_000000000000000000000000',
                    'failure_reason': 'expired_or_canceled_card',
                    'metadata': {
                        'reference': 'R-Test Transaction'
                    },
                    'payment_intent': 'pi_000000000000000000000000',
                    'status': 'failed',
                },
                'previous_attributes': {
                    'failure_balance_transaction': None,
                    'failure_reason': None,
                    'status': 'succeeded'
                }
            },
            'livemode': False,
            'pending_webhooks': 1,
            'type': 'charge.refund.updated'
        }

        cls.refund_notification_data = {
            'id': 'evt_000000000000000000000000',
            'object': 'event',
            'api_version': '2019-05-16',
            'created': 1646322995,
            'data': {
                'object': {
                    'id': 'ch_000000000000000000000000',
                    'object': 'charge',
                    'amount': 111111,
                    'amount_captured': 111111,
                    'amount_refunded': 111111,
                    'captured': True,
                    'created': 1646322927,
                    'currency': 'eur',
                    'description': 'Test Transaction',
                    'paid': True,
                    'refunded': True,
                    'refunds': {
                        'object': 'list',
                        'data': [{
                            'id': 're_000000000000000000000000',
                            'object': 'refund',
                            'amount': 111111,
                            'charge': 'ch_000000000000000000000000',
                            'created': 1646322994,
                            'currency': 'eur',
                            'metadata': {},
                            'payment_intent': 'pi_000000000000000000000000',
                            'reason': 'requested_by_customer',
                            'status': 'succeeded',
                        }],
                        'has_more': False,
                        'total_count': 1,
                        'url': '/v1/charges/ch_000000000000000000000000/refunds'
                    },
                    'status': 'succeeded',
                }
            },
            'livemode': False,
            'pending_webhooks': 1,
            'request': None,
            'type': 'charge.refunded'
            }

        cls.refund_updated_notification_data = {
            'id': 'evt_000000000000000000000000',
            'object': 'event',
            'api_version': '2019-05-16',
            'created': 1646322996,
            'data': {
                'object': {
                    'id': 're_000000000000000000000000',
                    'object': 'refund',
                    'amount': 111111,
                    'charge': 'ch_000000000000000000000000',
                    'created': 1646322994,
                    'currency': 'eur',
                    'metadata': {
                        'reference': 'R-Test Transaction'
                    },
                    'payment_intent': 'pi_000000000000000000000000',
                    'reason': 'requested_by_customer',
                    'status': 'succeeded',
                },
                'previous_attributes': {
                }
            },
            'livemode': False,
            'pending_webhooks': 1,
            'request': None,
            'type': 'charge.refund.updated'
        }

    @mute_logger('odoo.addons.payment_stripe.models.payment_transaction')
    def test_refund_from_odoo(self):
        self.acquirer.support_refund = 'partial' # Should simply not be False
        tx = self.create_transaction(
            'redirect', state='done'
        )
        tx._reconcile_after_done()  # Create the payment

        # Send the refund request
        with patch(
            'odoo.addons.payment_stripe.models.payment_acquirer.PaymentAcquirer'
            '._stripe_make_request',
            return_value=self.full_refund_response
        ):
            tx._send_refund_request()

        refund_tx = self.env['payment.transaction'].search([('source_transaction_id', '=', tx.id)])
        self.assertTrue(
            refund_tx,
            msg="Refunding a Stripe transaction should always create a refund transaction."
        )
        self.assertNotEqual(
            refund_tx.acquirer_reference,
            tx.acquirer_reference,
            msg="The acquirer reference of the refund transaction should different from that of "
                "the source transaction."
        )

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_refund_from_stripe(self):
        self.acquirer.support_refund = 'partial' # Should simply not be False
        tx = self.create_transaction(
            'redirect', state='done'
        )
        tx._reconcile_after_done()  # Create the payment

        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ), patch(
            'odoo.addons.payment_stripe.models.payment_acquirer.PaymentAcquirer'
            '._stripe_make_request',
            return_value={},
        ):
            self._make_json_request(url, data=self.refund_notification_data)

        refund_tx = self.env['payment.transaction'].search([('source_transaction_id', '=', tx.id)])
        self.assertTrue(
            refund_tx,
            msg="Refunding a Stripe transaction should always create a refund transaction."
        )
        self.assertEqual(
            refund_tx.state,
            'draft',
            msg="The transaction should be draft when created from the webhook and not yet "
                "post-processed."
        )

        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ):
            self._make_json_request(url, data=self.refund_updated_notification_data)

        self.assertEqual(
            refund_tx.state,
            'done',
            msg="The transaction should be done when created from the webhook and post-processed."
        )

    @mute_logger(
        'odoo.addons.payment_stripe.models.payment_transaction',
        'odoo.addons.payment_stripe.controllers.main'
    )
    def test_refund_pending(self):
        self.acquirer.support_refund = 'partial' # Should simply not be False
        tx = self.create_transaction(
            'redirect', state='done'
        )
        tx._reconcile_after_done()  # Create the payment

        # Send the refund request from odoo
        with patch(
            'odoo.addons.payment_stripe.models.payment_acquirer.PaymentAcquirer'
            '._stripe_make_request',
            return_value=self.pending_refund_response
        ):
            tx._send_refund_request()

        refund_tx = self.env['payment.transaction'].search([('source_transaction_id', '=', tx.id)])
        self.assertEqual(
            refund_tx.state,
            'pending',
            msg="The transaction should be pending when Stripe state is pending."
        )

        # Receiving the refund notification data from Stripe
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ):
            self._make_json_request(url, data=self.pending_refund_notification_data)

        self.assertEqual(
            refund_tx.state,
            'done',
            msg="The transaction should be done when Stripe state is succeeded."
        )

    @mute_logger(
        'odoo.addons.payment_stripe.models.payment_transaction',
        'odoo.addons.payment_stripe.controllers.main'
    )
    def test_refund_error(self):
        self.acquirer.support_refund = 'partial' # Should simply not be False
        tx = self.create_transaction(
            'redirect', state='done'
        )
        tx._reconcile_after_done()  # Create the payment

        # Send the refund request from odoo
        with patch(
            'odoo.addons.payment_stripe.models.payment_acquirer.PaymentAcquirer'
            '._stripe_make_request',
            return_value=self.full_refund_response
        ):
            tx._send_refund_request()

        # Receiving the refund notification data from Stripe
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController'
            '._verify_notification_signature'
        ):
            self._make_json_request(url, data=self.error_refund_notification_data)

        refund_tx = self.env['payment.transaction'].search([('source_transaction_id', '=', tx.id)])
        self.assertEqual(
            refund_tx.state,
            'error',
            msg="The transaction should be error when Stripe state is failed."
        )
