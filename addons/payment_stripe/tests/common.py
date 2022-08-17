# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class StripeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.stripe = cls._prepare_provider('stripe', update_values={
            'stripe_secret_key': 'sk_test_KJtHgNwt2KS3xM7QJPr4O5E8',
            'stripe_publishable_key': 'pk_test_QSPnimmb4ZhtkEy3Uhdm4S6J',
            'stripe_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprLVXT5jBLxB',
            'payment_icon_ids': [(5, 0, 0)],
        })

        cls.provider = cls.stripe

        cls.notification_data = {
            'data': {
                'object': {
                    'id': 'pi_3KTk9zAlCFm536g81Wy7RCPH',
                    'charges': {'data': [{'amount': 36800}]},
                    'customer': 'cus_LBxMCDggAFOiNR',
                    'payment_method': 'pm_1KVZSNAlCFm536g8sYB92I1G',
                    'description': cls.reference,
                    'status': 'succeeded',
                }
            },
            'type': 'payment_intent.succeeded'
        }

        cls.refund_object = {
            'amount': cls.amount,
            'charge': 'ch_000000000000000000000000',
            'currency': 'eur',
            'id': 're_000000000000000000000000',
            'object': 'refund',
            'payment_intent': 'pi_000000000000000000000000',
            'status': 'succeeded',
        }
        cls.refund_notification_data = {
            'data': {
                'object': {
                    'id': 'ch_000000000000000000000000',
                    'object': 'charge',
                    'amount': cls.amount,
                    'description': cls.reference,
                    'refunds': {
                        'object': 'list',
                        'data': [cls.refund_object],
                        'has_more': False,
                    },
                    'status': 'succeeded',
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
