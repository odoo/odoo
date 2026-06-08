# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.payment_custom.tests.common import PaymentCustomCommon


# AccountPaymentCommon enables post-processing (disabled in default payment test commons)
class AccountPaymentCustomCommon(AccountPaymentCommon, PaymentCustomCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wire_transfer_provider = cls._prepare_provider(
            code="custom", custom_mode="wire_transfer"
        )

        cls.provider = cls.wire_transfer_provider
        cls.currency = cls.currency_usd
