# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.payment.tests.common import PaymentCommon


class PayUCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.payu_merchant_key = 'AmJZXrY'
        cls.payu_merchant_salt = 'pFk8KYWAsYO73ywjFas5CnEX9nI3axCzY'

        cls.provider = cls._prepare_provider('payu', update_values={
            'payu_merchant_key': cls.payu_merchant_key,
            'payu_merchant_salt': cls.payu_merchant_salt,
            'payment_method_ids': [Command.set([cls.env.ref('payment.payment_method_card').id])],
        })

        cls.currency = cls.env['res.currency'].with_context(active_test=False).search([
            ('name', '=', 'INR'),
        ], limit=1)
        cls.currency.active = True

        cls.payment_method_id = cls.provider.payment_method_ids[:1].id
        cls.mihpayid = '17041aborcd'
        cls.reference = 'Test Transaction'

        # Simulated PayU payment webhook data (form-encoded POST from PayU).
        cls.webhook_payment_data = {
            'mihpayid': cls.mihpayid,
            'status': 'success',
            'txnid': cls.reference,
            'amount': str(cls.amount),
            'productinfo': 'Odoo-Product',
            'firstname': 'Norbert Buyer',
            'email': 'norbert.buyer@example.com',
            'phone': '0032 12 34 56 78',
            'udf1': 'payment',
            'udf2': '',
            'udf3': '',
            'udf4': '',
            'udf5': '',
            'udf6': '',
            'udf7': '',
            'udf8': '',
            'udf9': '',
            'udf10': '',
            'hash': 'dummy_hash',
            'key': cls.payu_merchant_key,
        }
        cls.webhook_payment_fail_data = {
            **cls.webhook_payment_data,
            'status': 'failure',
            'error_message': 'Payment was declined by the bank.',
        }
        cls.webhook_refund_data = {
            'action': 'refund',
            'mihpayid': '99887766',
            'status': 'success',
            'token': cls.reference,
            'amt': str(cls.amount),
            'key': cls.payu_merchant_key,
        }
