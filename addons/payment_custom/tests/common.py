# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain

from odoo.addons.payment.tests.common import PaymentCommon


class PaymentCustomCommon(PaymentCommon):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls._prepare_provider(code="custom", custom_mode="wire_transfer")
        cls.pay_on_invoice_provider = cls._prepare_provider(
            code="custom", custom_mode="pay_on_invoice"
        )

    @classmethod
    def _get_provider_domain(cls, code, custom_mode=None):
        domain = super()._get_provider_domain(code)
        if custom_mode:
            domain = Domain.AND([domain, [("custom_mode", "=", custom_mode)]])
        return domain
