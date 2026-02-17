from odoo.addons.payment.tests.common import PaymentCommon


class EcpayCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ecpay = cls._prepare_provider(
            'ecpay',
            update_values={
                'ecpay_merchant_id': '3002607',
                'ecpay_hash_key': 'pwFHCqoQZGmho4w6',
                'ecpay_hash_iv': 'EkRm7iFT261dpevs',
            },
        )
        cls.provider = cls.ecpay
        cls.amount = 2223
        cls.currency_twd = cls._enable_currency('TWD')
        cls.currency = cls.currency_twd
        cls.payment_result_data = {
            'CheckMacValue': '7F0C99607ACF1F0ADAAD43DAF8FE4D54D67B4FD459B3DD327A78A9F0FC2B514D',
            'CustomField1': '',
            'CustomField2': '',
            'CustomField3': '',
            'CustomField4': '',
            'MerchantID': '3002607',
            'MerchantTradeNo': 'S0000220251104095811',
            'PaymentDate': '2025/11/04 17:58:36',
            'PaymentType': 'Credit_CreditCard',
            'PaymentTypeChargeFee': '55',
            'RtnCode': '1',
            'RtnMsg': '交易成功',
            'SimulatePaid': '0',
            'StoreID': '',
            'TradeAmt': '2223',
            'TradeDate': '2025/11/04 17:58:11',
            'TradeNo': '2511041758118864',
        }
