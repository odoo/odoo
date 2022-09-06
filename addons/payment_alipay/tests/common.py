# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class AlipayCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency_yuan = cls._prepare_currency('CNY')
        cls.alipay = cls._prepare_acquirer('alipay', update_values={
            'alipay_merchant_partner_id': 'dummy',
            'alipay_md5_signature_key': 'dummy',
            'alipay_seller_email': 'dummy',
            'fees_active': False,  # Only activate fees in dedicated tests
        })

        # override defaults for helpers
        cls.acquirer = cls.alipay
        cls.currency = cls.currency_yuan

        cls.notification_data = {
            'currency': 'CNY',
            'notify_id': '1234567890123456789012345678901234',
            'notify_time': '2021-12-01 01:01:01',
            'notify_type': 'trade_status_sync',
            'out_trade_no': cls.reference,
            'sign': '782b6d1015549f847e2ab27d1edb65c7',
            'sign_type': 'MD5',
            'total_fee': '1111.11',
            'trade_no': '2021111111111111111111111111',
            'trade_status': 'TRADE_FINISHED',
        }
