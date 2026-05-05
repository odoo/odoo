# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class SSLCommerzCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sslcommerz = cls._prepare_provider(
            "sslcommerz",
            update_values={
                "sslcommerz_store_id": "test_store",
                "sslcommerz_store_passwd": "test_password",
            },
        )
        cls.provider = cls.sslcommerz
        cls.currency_bdt = cls._enable_currency("BDT")
        cls.currency = cls.currency_bdt

        cls.payment_data = {
            "tran_id": cls.reference,
            "status": "VALID",
            "val_id": "260101012345",
            "bank_tran_id": "230101012345",
            "currency_amount": cls.amount,
            "currency_type": cls.currency.name,
        }
