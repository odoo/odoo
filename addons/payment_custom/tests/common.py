# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.osv.expression import AND

from odoo.addons.payment.tests.common import PaymentCommon


class PaymentCustomCommon(PaymentCommon):

    @classmethod
    def _get_provider_domain(cls, code, custom_mode=None):
        domain = super()._get_provider_domain(code)
        if custom_mode:
            domain = AND([domain, [('custom_mode', '=', custom_mode)]])
        return domain
