# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PaypalCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.paypal = cls._prepare_provider('paypal', update_values={
            'paypal_email_account': 'dummy@test.mail.com',
            'paypal_client_id': 'dummy_client_id',
            'paypal_client_secret': 'dummy_secret',
        })

        # Override default values
        cls.provider = cls.paypal
        cls.currency = cls.currency_euro
        cls.order_id = '123DUMMY456'

        cls.payment_data = {
            'event_type': 'CHECKOUT.ORDER.APPROVED',
            'resource': {
                'id': cls.order_id,
                'intent': 'CAPTURE',
                'status': 'COMPLETED',
                'payment_source': {
                    'paypal': {
                        'account_id': '59XDVNACRAZZJ',
                    }},
                'purchase_units': [{
                    'amount': {
                        'currency_code': cls.currency.name,
                        'value': str(cls.amount),
                    },
                    'reference_id': cls.reference,
                }],
            }
        }

        cls.completed_order = {
            'status': 'COMPLETED',
            'payment_source': {
                'paypal': {'account_id': '59XDVNACRAZZJ'},
            },
            'purchase_units': [{
                'reference_id': cls.reference,
                'payments': {
                    'captures': [{
                        'amount': {
                            'currency_code': cls.currency.name,
                            'value': str(cls.amount),
                        },
                        'status': 'COMPLETED',
                        'id': cls.order_id,
                    }],
                },
            }],
        }
