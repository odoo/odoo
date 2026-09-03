# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.http_common import PaymentHttpCommon


class NuveiCommon(PaymentHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.nuvei = cls._prepare_provider('nuvei', update_values={
            'nuvei_merchant_identifier': '123456abc',
            'nuvei_site_identifier': '1234',
            'nuvei_secret_key': 'dummy',
        })

        cls.provider = cls.nuvei

        cls.payment_data = {
            "ppp_status": "OK",
            "currency": "USD",
            "PPP_TransactionID": "489616878",
            "payment_method": "cc_card",
            "productId": cls.reference,
            "responseTimeStamp": "2024-09-06.22:27:37",
            "message": "Success",
            "Error": "Success",
            "Status": "APPROVED",
            "advanceResponseChecksum": "5361e831a6ed08ddd47d52fc511a605518e"
                                       "2696f302b301d709f950e91398f63",
            "totalAmount": cls.amount,
            "TransactionID": "7110000000004858227",
            "item_amount_1": cls.amount,
            "item_quantity_1": "1",
        }
