# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PortalEntryPayment(models.Model):
    _inherit = "portal.entry"

    def _filter_visible_portal_cards(self):
        visible_entries = super()._filter_visible_portal_cards()
        payment_methods_entry = self.env.ref("payment.payment_methods_portal_entry", raise_if_not_found=False)
        if payment_methods_entry and payment_methods_entry in self:
            partner_sudo = self.env.user.partner_id.sudo()
            providers_sudo = (
                self
                .env["payment.provider"]
                .sudo()
                ._find_available_providers(
                    self.env.company.id,
                    partner_sudo.id,
                    0.0,
                    force_tokenization=True,
                    is_validation=True,
                )
            )
            methods_allowing_tokenization = providers_sudo._find_available_payment_methods(
                partner_sudo.id, force_tokenization=True
            )
            existing_tokens = (
                partner_sudo.payment_token_ids
                + partner_sudo.commercial_partner_id.payment_token_ids
            )
            if not (methods_allowing_tokenization or existing_tokens):
                visible_entries -= payment_methods_entry
        return visible_entries
