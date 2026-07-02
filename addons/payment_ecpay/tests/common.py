# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class EcpayCommon(PaymentCommon):
    _test_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ecpay = cls._prepare_provider(
            "ecpay",
            update_values={
                "ecpay_merchant_id": "mock-merchant-id",
                "ecpay_hash_key": "mock-hash-key",
                "ecpay_hash_iv": "mock-hash-iv",
            },
        )
        cls.provider = cls.ecpay
        cls.currency_twd = cls._enable_currency("TWD")
        cls.currency = cls.currency_twd
        cls.webhook_payment_data_signature = (
            "FDA651CFEC09D25FC20B176675FA45722926F249EA663E716069C9A4B9138495"
        )
        cls.payment_result_data = {
            "MerchantID": "mock-merchant-id",
            "MerchantTradeNo": cls.reference,
            "PaymentDate": "2026/03/25 11:39:08",
            "PaymentType": "DigitalPayment_IPASS",
            "PaymentTypeChargeFee": "0",
            "RtnCode": "1",
            "RtnMsg": "Succeeded",
            "SimulatePaid": "0",
            "TradeAmt": int(cls.amount),
            "TradeDate": "2026/03/25 11:39:03",
            "TradeNo": "2603251139038665",
        }
