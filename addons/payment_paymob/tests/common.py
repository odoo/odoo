# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PaymobCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.country_egypt = cls.quick_ref('base.eg')
        cls.paymob = cls._prepare_provider('paymob', update_values={
            'paymob_public_key': 'dummy_pk',
            'paymob_secret_key': 'dummy_sk',
            'paymob_hmac_key': 'dummy_hmac',
            'paymob_api_key': 'dummy_api_key',
            'paymob_account_country_id': cls.country_egypt,
        })

        # Override default values
        cls.provider = cls.paymob
        cls.currency = cls._enable_currency('EGP')
        cls.hmac_signature = '51860052ecc6d9f08ac30a549359019e2eee837913b5673094c242c817ddf57c055ba5e3e9c0894b1171e62c2d37cd55ff98a46a0e28e1ccf2e4a907e6683aa5'

        cls.order_id = '123DUMMY456'

        cls.redirection_data = {
            'amount_cents': '111111',
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
            'amount_cents': 111111,
            'created_at': "2025-04-01T17:29:16.967925",
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
