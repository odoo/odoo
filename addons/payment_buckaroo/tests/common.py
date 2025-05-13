# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class BuckarooCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.buckaroo = cls._prepare_provider('buckaroo', update_values={
            'buckaroo_website_key': 'dummy',
            'buckaroo_secret_key': 'test_key_123',
        })

        # Override defaults
        cls.provider = cls.buckaroo
        cls.currency = cls.currency_euro

        cls.sync_payment_data = {
            'brq_payment': 'ABCDEF0123456789ABCDEF0123456789',
            'brq_payment_method': 'paypal',
            'brq_statuscode': '190',  # confirmed
            'brq_statusmessage': 'Transaction successfully processed',
            'brq_invoicenumber': cls.reference,
            'brq_amount': str(cls.amount),
            'brq_currency': cls.currency.name,
            'brq_timestamp': '2022-01-01 12:00:00',
            'brq_transactions': '0123456789ABCDEF0123456789ABCDEF',
            'brq_signature': '5d389aa4f563cd99666a2e6bef79da3d4a32eb50',
        }

        cls.async_payment_data = {
            'brq_transactions': '0123456789ABCDEF0123456789ABCDEF',
            'brq_transaction_method': 'paypal',
            'brq_statuscode': '190',  # confirmed
            'brq_statusmessage': 'Transaction successfully processed',
            'brq_invoicenumber': cls.reference,
            'brq_amount': str(cls.amount),
            'brq_currency': cls.currency.name,
            'brq_timestamp': '2022-01-01 12:00:00',
            'brq_transaction_type': 'V010',
            'brq_signature': 'fa3444e135c366a1d2660adb406fb47efdc28130',
        }
