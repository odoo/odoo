# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.payment.tests.common import PaymentCommon


class PayfastCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency_zar = cls._enable_currency("ZAR")

        cls.payfast = cls._prepare_provider(
            "payfast",
            update_values={
                "payfast_merchant_id": "10000100",
                "payfast_merchant_key": "46f0cd694581a",
                "payfast_passphrase": "jt7NOE43FZPn",
                "available_currency_ids": [Command.set(cls.currency_zar.ids)],
            },
        )

        cls.provider = cls.payfast
        cls.currency = cls.currency_zar

        # A valid ITN notification, as Payfast would post it; the signature was computed
        # independently against this exact payload and the passphrase set above.
        cls.notification_data = {
            "m_payment_id": cls.reference,
            "pf_payment_id": "1089250",
            "payment_status": "COMPLETE",
            "item_name": cls.reference,
            "amount_gross": f"{cls.amount:.2f}",
            "merchant_id": "10000100",
            "signature": "da1c5fc6f8613150cf8e9c0e98b24cef",
        }
