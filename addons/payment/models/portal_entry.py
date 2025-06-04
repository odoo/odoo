# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class PortalEntryPayment(models.Model):
    _inherit = 'portal.entry'

    def should_show_portal_card(self):
        res = super().should_show_portal_card()
        external_id = self.get_external_id().get(self.id, '')
        if external_id == "payment.portal_payment_orders":
            partner_sudo = request.env.user.partner_id.sudo()
            providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
                request.env.company.id,
                partner_sudo.id,
                0.0,
                force_tokenization=True,
                is_validation=True,
            )
            methods_allowing_tokenization = request.env['payment.method'].sudo()._get_compatible_payment_methods(
                providers_sudo.ids,
                partner_sudo.id,
                force_tokenization=True,
            )
            existing_tokens = (
                partner_sudo.payment_token_ids
                + partner_sudo.commercial_partner_id.payment_token_ids
            )
            res &= bool(methods_allowing_tokenization or existing_tokens)
        return res
