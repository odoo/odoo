# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class QFPayCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.qfpay = cls._prepare_provider(
            'qfpay',
            update_values={
                'qfpay_app_code': 'mock-app-code',
                'qfpay_app_key': 'mock-app-key',
                'qfpay_mchntid': 'mock-merchant-id',
            },
        )
        cls.provider = cls.qfpay
        cls.amount = 750.0
        cls.currency_hkd = cls._enable_currency('HKD')
        cls.currency = cls.currency_hkd

        cls.payment_result_data = {
            'out_trade_no': cls.reference,
            'txamt': str(int(cls.amount * 100)),  # QFPay expects cents
            'txcurrcd': cls.currency.name,
            'respcd': '0000',  # '0000' is QFPay's success code
            'respmsg': 'Success',
            'sign': 'dummy-signature',
        }

        # For QFPay, the webhook data is usually identical in structure to the return data
        cls.webhook_data = cls.payment_result_data.copy()
