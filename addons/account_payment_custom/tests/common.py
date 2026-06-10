# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.payment_custom.tests.common import PaymentCustomCommon


# AccountPaymentCommon enables post-processing (disabled in default payment test commons)
class AccountPaymentCustomCommon(AccountPaymentCommon, PaymentCustomCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bank_account = cls.env["res.partner.bank"].create({
            "account_number": "BANK123456789",
            "partner_id": cls.env.company.partner_id.id,
        })
        cls.wire_transfer_provider = cls._prepare_provider(
            code="custom",
            custom_mode="wire_transfer",
            update_values={"bank_account_id": cls.bank_account.id},
        )

        cls.provider = cls.wire_transfer_provider
        cls.currency = cls.currency_usd
