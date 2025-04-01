# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PaymobCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.paymob = cls._prepare_provider('paymob', update_values={
            'paymob_public_key': 'dummy_pk',
            'paymob_secret_key': 'dummy_sk',
            'paymob_hmac_key': 'dummy_hmac',
            'paymob_api_key': 'dummy_api_key',
        })

        # Override default values
        cls.provider = cls.paymob
        cls.currency = cls._enable_currency('EGP')
        cls.hmac_signature = '048064cfe22340c98a4370a7650a429420cb5a9c160888b17bb7fb3510a818f6fe3c2e984c0e0c1e3f448e9cfea62c5626b24411eb3f98784e284620b402e927'

        cls.country_egypt = cls.quick_ref('base.eg')
        cls.order_id = '123DUMMY456'

        cls.redirection_data = {
            'amount_cents': '10000',
            'created_at': '2025-04-01T17:29:16.967925',
            'currency': cls.currency.name,
            'error_occured': 'false',
            'has_parent_transaction': 'false',
            'id': 'dummy_id',
            'integration_id': '1234',
            'is_3d_secure': 'true',
            'is_auth': 'false',
            'is_capture': 'false',
            'is_refunded': 'false',
            'is_standalone_payment': 'true',
            'is_voided': 'false',
            'order': '123',
            'owner': '12',
            'pending': 'false',
            'source_data.pan': '1111',
            'source_data.sub_type': 'Visa',
            'source_data.type': 'card',
            'success': 'true',
            'data.message': 'Approved',
            'hmac': cls.hmac_signature,
            'merchant_order_id': cls.order_id,
        }
        cls.webhook_data = {
            'amount_cents': 10000,
            'created_at': '2025-04-01T17:29:16.967925',
            'currency': cls.currency.name,
            'error_occured': False,
            'has_parent_transaction': False,
            'id': 'dummy_id',
            'integration_id': 1234,
            'is_3d_secure': True,
            'is_auth': False,
            'is_capture': False,
            'is_hidden': False,
            'is_refunded': False,
            'is_standalone_payment': True,
            'is_voided': False,
            'order': {
                'id': 123,
                'merchant_order_id': cls.order_id,
            },
            'owner': 12,
            'pending': False,
            'source_data': {
                'pan': '1111',
                'sub_type': 'Visa',
                'type': 'card'
            },
            'success': True,
            'data': {
                'message': 'Approved',
            },
        }
