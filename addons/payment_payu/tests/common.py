# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.common import PaymentCommon


class PayuCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payu = cls._prepare_provider(
            "payu", update_values={"payu_key_id": "test_key_id", "payu_merchant_salt": "test_salt"}
        )
        cls.provider = cls.payu
        cls.partner_first_name, cls.partner_last_name = payment_utils.split_partner_name(
            cls.partner.name
        )
        cls.payment_data = {
            "txnid": cls.reference,
            "amount": cls.amount,
            "status": "success",
            "productinfo": "Odoo Payment",
            "firstname": cls.partner_first_name,
            "email": cls.partner.email,
            "phone": cls.partner.phone,
            "mihpayid": "test_123",
        }
