# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.payment_stripe import const


class StripeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.stripe = cls._prepare_provider('stripe', update_values={
            'stripe_secret_key': 'sk_test_KJtHgNwt2KS3xM7QJPr4O5E8',
            'stripe_publishable_key': 'pk_test_QSPnimmb4ZhtkEy3Uhdm4S6J',
            'stripe_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprLVXT5jBLxB',
            'payment_method_ids': [(5, 0, 0)],
        })

        cls.provider = cls.stripe

        cls.notification_amount_and_currency = {
            'amount': payment_utils.to_minor_currency_units(cls.amount, cls.currency),
            'currency': cls.currency.name.lower(),
        }
        cls.notification_data = {
            'data': {
                'object': {
                    'id': 'pi_3KTk9zAlCFm536g81Wy7RCPH',
                    'charges': {'data': [{'amount': 36800}]},
                    'customer': 'cus_LBxMCDggAFOiNR',
                    'payment_method': {'type': 'pm_1KVZSNAlCFm536g8sYB92I1G'},
                    'description': cls.reference,
                    'status': 'succeeded',
                    **cls.notification_amount_and_currency,
                }
            },
            'type': 'payment_intent.succeeded'
        }

        cls.refund_object = {
            'charge': 'ch_000000000000000000000000',
            'id': 're_000000000000000000000000',
            'object': 'refund',
            'payment_intent': 'pi_000000000000000000000000',
            'status': 'succeeded',
            **cls.notification_amount_and_currency,
        }
        cls.refund_notification_data = {
            'data': {
                'object': {
                    'id': 'ch_000000000000000000000000',
                    'object': 'charge',
                    'description': cls.reference,
                    'refunds': {
                        'object': 'list',
                        'data': [cls.refund_object],
                        'has_more': False,
                    },
                    'status': 'succeeded',
                    **cls.notification_amount_and_currency,
                }
            },
            'type': 'charge.refunded'
        }
        cls.canceled_refund_notification_data = {
            'data': {
                'object': dict(cls.refund_object, status='failed'),
            },
            'type': 'charge.refund.updated',
        }

    def _mock_setup_intent_request(self, *args, **kwargs):
        # See: https://docs.stripe.com/api/setup_intents/confirm
        mandate_options = {
            'amount': 1500000,
            'amount_type': 'maximum',
            'currency': self.currency.name.lower(),
        } if self.currency.name in const.INDIAN_MANDATES_SUPPORTED_CURRENCIES else None
        return {
            'object': 'setup_intent',
            'id': 'seti_XXXX',
            'customer': 'cus_XXXX',
            'description': self.reference,
            'payment_method': {
                'id': 'pm_XXXX',
                'type': 'card',
                'card': {'brand': 'dummy'},
            },
            'payment_method_options': {'card': {
                'mandate_options': mandate_options,
            }},
            'status': 'succeeded',
        }
