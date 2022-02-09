# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class StripeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.stripe = cls._prepare_acquirer('stripe', update_values={
            'stripe_secret_key': 'sk_test_KJtHgNwt2KS3xM7QJPr4O5E8',
            'stripe_publishable_key': 'pk_test_QSPnimmb4ZhtkEy3Uhdm4S6J',
            'stripe_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprLVXT5jBLxB',
            'payment_icon_ids': [(5, 0, 0)],
        })

        cls.acquirer = cls.stripe

        cls.notification_data = {
            'api_version': '2019-05-16',
            'created': 1326853478,
            'data': {
                'object': {
                    'after_expiration': None,
                    'allow_promotion_codes': None,
                    'amount_subtotal': None,
                    'amount_total': None,
                    'automatic_tax': {
                        'enabled': False,
                        'status': None,
                    },
                    'billing_address_collection': None,
                    'cancel_url': 'https://example.com/payment/stripe/checkout_return?reference=Test Transaction',
                    'client_reference_id': cls.reference,
                    'consent': None,
                    'consent_collection': None,
                    'currency': None,
                    'customer': None,
                    'customer_creation': None,
                    'customer_details': None,
                    'customer_email': None,
                    'expires_at': 1642614393,
                    'id': 'cs_00000000000000',
                    'livemode': False,
                    'locale': None,
                    'metadata': {},
                    'mode': 'payment',
                    'object': 'checkout.session',
                    'payment_intent': 'pi_00000000000000',
                    'payment_method_options': {},
                    'payment_method_types': ['card'],
                    'payment_status': 'unpaid',
                    'phone_number_collection': {'enabled': False},
                    'recovered_from': None,
                    'setup_intent': None,
                    'shipping': None,
                    'shipping_address_collection': None,
                    'shipping_options': [],
                    'shipping_rate': None,
                    'status': 'expired',
                    'submit_type': None,
                    'subscription': None,
                    'success_url': 'https://example.com/payment/stripe/checkout_return?reference=Test Transaction',
                    'total_details': None,
                    'url': None,
                },
            },
            'id': 'evt_00000000000000',
            'livemode': False,
            'object': 'event',
            'pending_webhooks': 1,
            'request': None,
            'type': 'checkout.session.completed',
        }
