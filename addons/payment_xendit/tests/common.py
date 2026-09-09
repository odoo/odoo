# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class XenditCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.xendit = cls._prepare_provider('xendit', update_values={
            'xendit_secret_key': 'xnd_secret_key',
            'xendit_webhook_token': 'xnd_webhook_token',
        })
        cls.provider = cls.xendit
        cls.webhook_notification_data = {
            'payment_session_id': 'ps-64a8f9c614802d6c402cd82d',
            'reference_id': cls.reference,
            'session_type': 'PAY',
            'mode': 'PAYMENT_LINK',
            'amount': 1740,
            'currency': 'IDR',
            'country': 'ID',
            'status': 'COMPLETED',
            'created': '2023-07-12T09:31:13.111Z',
            'updated': '2023-07-12T09:31:23.577Z',
            'description': cls.reference,
            'customer_id': 'cust-64118d86854d7d89206e732d',
            'allowed_payment_channels': ['BNI'],
            'payment_link_url': 'https://xen.to/kGxPCi60',
            'payment_id': 'py-ac1fcd3e-21c5-4c70-bb06-fa3c34e19e0c',
            'business_id': '64118d86854d7d89206e732d',
        }
        cls.payment_request_notification_data = {
            'payment_request_id': 'pr-64a8d9c614802d6c402cd82d',
            'reference_id': cls.reference,
            'type': 'PAY',
            'status': 'SUCCEEDED',
            'currency': 'IDR',
            'request_amount': 11100,
            'payment_token_id': 'pt-6275md8ac5f00da60017cdc669',
            'channel_code': 'CARDS',
            'business_id': '64118d86854d7d89206e732d',
        }
        cls.payment_token_data = {
            'payment_token_id': 'pt-6275md8ac5f00da60017cdc669',
            'channel_code': 'CARDS',
            'channel_properties': {
                'card_details': {
                    'masked_card_number': '520000XXXXXX2151',
                    'cardholder_first_name': 'John',
                    'cardholder_last_name': 'Doe',
                },
            },
            'status': 'ACTIVE',
        }
        cls.token_activation_notification_data = {
            'payment_token_id': 'pt-6275md8ac5f00da60017cdc669',
            'reference_id': cls.reference,
            'status': 'ACTIVE',
            'channel_code': 'CARDS',
            'channel_properties': {
                'card_details': {
                    'masked_card_number': '400000XXXXXX1000',
                    'cardholder_first_name': 'Test',
                    'cardholder_last_name': 'User',
                },
                'transaction_sequence': 'INITIAL',
            },
        }
        cls.payment_request_requires_action_data = {
            'payment_request_id': 'pr-64a8d9c614802d6c402cd82d',
            'reference_id': cls.reference,
            'type': 'PAY',
            'status': 'REQUIRES_ACTION',
            'currency': 'IDR',
            'request_amount': 11100,
            'actions': [{
                'type': 'REDIRECT_CUSTOMER',
                'descriptor': 'WEB_URL',
                'value': 'https://redirect.xendit.co/v3/payment_requests/64a8d9c6/pre_checkout',
            }],
        }
