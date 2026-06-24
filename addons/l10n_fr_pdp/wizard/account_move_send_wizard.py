from odoo import models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _get_peppol_checkbox_label(self, default_label):
        self.ensure_one()
        pdp_partner = self.move_id.partner_id.commercial_partner_id.with_company(self.company_id)
        if not pdp_partner.l10n_fr_is_pdp:
            return super()._get_peppol_checkbox_label(default_label)
        return self.env._("French E-Invoicing")

    def _get_peppol_checkbox_addendum_disable_reason(self):
        self.ensure_one()
        pdp_partner = self.move_id.partner_id.commercial_partner_id.with_company(self.company_id)
        if not pdp_partner.l10n_fr_is_pdp:
            return super()._get_peppol_checkbox_addendum_disable_reason()
        partner_is_valid = pdp_partner.peppol_verification_state == 'valid'
        verification_display_state_map = dict(pdp_partner._fields['pdp_verification_display_state']._description_selection(self.env))
        reason = None
        if pdp_partner._l10n_fr_pdp_is_b2c():
            reason = self.env._("no VAT")
        if not partner_is_valid:
            reason = verification_display_state_map[pdp_partner.pdp_verification_display_state]
        if self.move_id.peppol_is_sent:
            reason = self.env._("Previously sent")
        if reason:
            return f" ({reason})"
        return ""
