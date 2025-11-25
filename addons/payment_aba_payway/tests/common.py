from odoo.addons.payment.tests.common import PaymentCommon


class AbaPaywayCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.aba_payway = cls._prepare_provider('aba_payway', update_values={
            'payway_merchant_id': '3002607',
            'payway_api_key': 'pwFHCqoQZGmho4w6',
        })
        cls.provider = cls.aba_payway
        cls.amount = 2213
        cls.currency_khr = cls._enable_currency('KHR')
        cls.currency = cls.currency_khr
        cls.payment_result_data = {
            'apv': '1764310810',
            'status': 0,
            'tran_id': 'tx-20251128061000'
        }
        cls.check_transaction_data = {
            'data': {
                'payment_status_code': 0,
                'total_amount': 2213,
                'original_amount': 2213,
                'refund_amount': 0,
                'discount_amount': 0.0,
                'payment_amount': 2213,
                'payment_currency': 'KHR',
                'apv': '1764310810',
                'payment_status': 'APPROVED',
                'transaction_date': '2025-11-28 13:20:06'
            },
            'status': {
                'code': '00',
                'message': 'Success!',
                'tran_id': 'tx-20251128061000'
            }
        }
        cls.enriched_payment_result_data = cls.payment_result_data.copy()
        cls.enriched_payment_result_data['data'] = cls.check_transaction_data['data']
