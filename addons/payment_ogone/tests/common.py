# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class OgoneCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ogone = cls._prepare_provider('ogone', update_values={
            'ogone_pspid': 'dummy',
            'ogone_userid': 'dummy',
            'ogone_password': 'dummy',
            'ogone_shakey_in': 'dummy',
            'ogone_shakey_out': 'dummy',
            'ogone_hash_function': 'sha1',
        })

        cls.provider = cls.ogone
        cls.currency = cls.currency_euro

        cls.notification_data = {
            'AAVADDRESS': 'NO',
            'amount': '1111.11',
            'CARDNO': 'XXXXXXXXXXXX1111',
            'CN': 'Dummy Customer Name',
            'currency': 'USD',
            'IP': '101.00.111.22',
            'NCERROR': '0',
            'orderID': cls.reference,
            'PAYID': '01234567899',
            'PM': 'CreditCard',
            'SHASIGN': '2CE444D2260D914EA7E56450B7B28F189238553B',
            'STATUS': '9',  # 'Payment requested' (done)
            'TRXDATE': '01/31/22',
        }
