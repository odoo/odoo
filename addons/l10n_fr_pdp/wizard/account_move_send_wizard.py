from odoo import models
from odoo.exceptions import RedirectWarning


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _get_peppol_checkbox_label(self, default_label):
        self.ensure_one()
        pdp_partner = self.move_id.partner_id.commercial_partner_id.with_company(self.company_id)
        if self.company_id._get_peppol_proxy_type() != 'pdp' or pdp_partner._get_pdp_receiver_identification_info()[0] != 'pdp':
            return super()._get_peppol_checkbox_label(default_label)
        return self.env._("French E-Invoicing")

    def _get_peppol_checkbox_addendum_disable_reason(self):
        self.ensure_one()
        pdp_partner = self.move_id.partner_id.commercial_partner_id.with_company(self.company_id)
        if pdp_partner._get_pdp_receiver_identification_info()[0] != 'pdp':
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

    def action_send_and_print(self, allow_fallback_pdf=False):
        auth_totp_disabled = not self.env.user.totp_enabled and not bool(self.env['ir.config_parameter'].sudo().get_param('auth_totp.policy'))
        if self.company_id._get_peppol_proxy_type() == 'pdp' and auth_totp_disabled:
            raise RedirectWarning(
                message=self.env._("To use the French e-invoicing, you need to enable the two-factor authentication."),
                action=self.env.user._get_records_action(
                    target='new',
                    views=[(self.env.ref('base.view_users_form_simple_modif').id, "form")],
                ),
                button_text=self.env._("Go to the Preferences panel"),
            )
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
