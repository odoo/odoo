# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.common import PaymentCommon


class WorldlineCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.worldline = cls._prepare_provider('worldline', update_values={
            'worldline_pspid': 'dummy',
            'worldline_api_key': 'dummy',
            'worldline_api_secret': 'dummy',
            'worldline_webhook_key': 'dummy',
            'worldline_webhook_secret': 'dummy',
        })

        cls.provider = cls.worldline
        cls.currency = cls.currency_euro
        cls.notification_amount_and_currency = {
            'amount': payment_utils.to_minor_currency_units(cls.amount, cls.currency),
            'currencyCode': cls.currency.name,
        }

        cls.payment_data = {
            'payment': {
                'paymentOutput': {
                    'references': {
                        'merchantReference': cls.reference,
                    },
                    'cardPaymentMethodSpecificOutput': {
                        'paymentProductId': 1,
                        'card': {
                            'cardNumber': "******4242"
                        },
                        'token': 'whateverToken'
                    },
                    'amountOfMoney': cls.notification_amount_and_currency,
                },
                'id': '1234567890_0',
                'status': 'CAPTURED',
            },
        }

        cls.payment_data_insufficient_funds = {
            'errorId': 'ffffffff-fff-fffff-ffff-ffffffffffff',
            'errors': [{
                'category': 'IO_ERROR',
                'code': '9999',
                'errorCode': '30511001',
                'httpStatusCode': 402,
                'id': 'EXTERNAL_ACQUIRER_ERROR',
                'message': '',
                'retriable': False,
            }],
            'paymentResult': {
                'creationOutput': {
                    'externalReference': 'aaaaaaaa-5555-eeee-eeee-eeeeeeeeeeee',
                    'isNewToken': False,
                    'token': 'aaaaaaaa-5555-eeee-eeee-eeeeeeeeeeee',
                    'tokenizationSucceeded': False,
                },
                'payment': {
                    'id': '7777777000_0',
                    'paymentOutput': {
                        'acquiredAmount': {'amount': 0, 'currencyCode': 'EUR'},
                        'amountOfMoney': cls.notification_amount_and_currency,
                        'cardPaymentMethodSpecificOutput': {
                            'acquirerInformation': {'name': "Test Pay"},
                            'card': {
                                'bin': '50010000',
                                'cardNumber': '************7777',
                                'countryCode': 'BE',
                                'expiryDate': '1244',
                            },
                            'fraudResults': {'cvvResult': 'P', 'fraudServiceResult': 'accepted'},
                            'paymentProductId': 3,
                            'threeDSecureResults': {'eci': '9', 'xid': 'zOMTQ5TcODUxMg=='},
                            'token': 'aaaaaaaa-5555-eeee-eeee-eeeeeeeeeeee',
                        },
                        'customer': {'device': {'ipAddressCountryCode': '99'}},
                        'paymentMethod': 'card',
                        'references': {'merchantReference': cls.reference},
                    },
                    'status': 'REJECTED',
                    'statusOutput': {
                        'errors': [{
                            'category': 'IO_ERROR',
                            'code': '9999',
                            'errorCode': '30511001',
                            'httpStatusCode': 402,
                            'id': 'EXTERNAL_ACQUIRER_ERROR',
                            'message': '',
                            'retriable': False,
                        }],
                        'isAuthorized': False,
                        'isCancellable': False,
                        'isRefundable': False,
                        'statusCategory': 'UNSUCCESSFUL',
                        'statusCode': 2,
                    },
                },
            },
        }

        cls.payment_data_expired_card = {
            'apiFullVersion': 'v1.1',
            'apiVersion': 'v1',
            'created': '2025-02-20T03:09:47.3706109+01:00',
            'id': 'ffffffff-fff-fffff-ffff-ffffffffffff',
            'merchantId': 'MyCompany',
            'payment': {
                'id': '9999999999_0',
                'paymentOutput': {
                    'acquiredAmount': {'amount': 0, 'currencyCode': 'EUR'},
                    'amountOfMoney': cls.notification_amount_and_currency,
                    'cardPaymentMethodSpecificOutput': {
                        'acquirerInformation': {'name': "Test Pay"},
                        'card': {
                            'bin': '47777700',
                            'cardNumber': '************9999',
                            'countryCode': 'FR',
                            'expiryDate': '1234',
                        },
                        'fraudResults': {'cvvResult': 'P', 'fraudServiceResult': 'accepted'},
                        'paymentProductId': 1,
                        'threeDSecureResults': {'eci': '9'},
                        'token': 'ODOO-ALIAS-eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'},
                    'customer': {'device': {'ipAddressCountryCode': '99'}},
                    'paymentMethod': 'card',
                    'references': {'merchantReference': cls.reference},
                },
                'status': 'REJECTED',
                'statusOutput': {
                    'errors': [{
                        'category': 'PAYMENT_PLATFORM_ERROR',
                        'code': '9999',
                        'errorCode': '30331001',
                        'httpStatusCode': 402,
                        'id': 'INVALID_CARD',
                        'message': '',
                        'retriable': False,
                    }],
                    'isAuthorized': False,
                    'isCancellable': False,
                    'isRefundable': False,
                    'statusCategory': 'UNSUCCESSFUL',
                    'statusCode': 2
                },
            },
            'type': 'payment.rejected',
        }
