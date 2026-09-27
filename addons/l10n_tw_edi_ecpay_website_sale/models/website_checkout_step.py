# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WebsiteCheckoutStep(models.Model):
    _inherit = 'website.checkout.step'

    def _validate_completion(self, order_sudo, **kwargs):
        if self.step_href == '/shop/l10n_tw_invoicing_info':
            return self._check_l10n_tw_invoicing_info_completion(order_sudo, **kwargs)
        return super()._validate_completion(order_sudo, **kwargs)

    def _check_l10n_tw_invoicing_info_completion(self, order_sudo, **_kwargs):
        if (
            self.website_id.company_id._is_ecpay_enabled()
            and not order_sudo.partner_id.l10n_tw_edi_require_paper_format
            and not (order_sudo.l10n_tw_edi_carrier_type or order_sudo.l10n_tw_edi_love_code)
        ):
            return '/shop/l10n_tw_invoicing_info'
