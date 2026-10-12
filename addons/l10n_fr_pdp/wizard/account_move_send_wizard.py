from odoo import api, fields, models

from odoo.addons.account.wizard.account_move_send_wizard import AccountMoveSendWizard as AccountMoveSendWizardAccount


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    l10n_fr_pdp_force_send_einvoicing = fields.Boolean(
        string='Force French E-Invoicing',
        help='Send the invoice to the DGFiP via your Approved Platform even when the buyer '
             'is not registered in the annuaire yet.',
    )
    l10n_fr_pdp_show_force_send = fields.Boolean(
        compute='_compute_l10n_fr_pdp_show_force_send',
    )

    @api.depends('move_id', 'company_id')
    def _compute_l10n_fr_pdp_show_force_send(self):
        for wizard in self:
            partner = wizard.move_id.commercial_partner_id.with_company(wizard.company_id)
            wizard.l10n_fr_pdp_show_force_send = bool(wizard.move_id) and partner._l10n_fr_pdp_is_not_in_annuaire()

    @api.onchange('l10n_fr_pdp_force_send_einvoicing')
    def _onchange_l10n_fr_pdp_force_send_einvoicing(self):
        self._compute_sending_method_checkboxes()
        if self.l10n_fr_pdp_force_send_einvoicing and self.sending_method_checkboxes.get('peppol'):
            peppol_checkbox = self.sending_method_checkboxes['peppol']
            self.sending_method_checkboxes = {
                **self.sending_method_checkboxes,
                'peppol': {
                    **peppol_checkbox,
                    'checked': True,
                    'readonly': False,
                },
            }

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _get_peppol_checkbox_label(self, default_label):
        self.ensure_one()
        if not self.company_id._l10n_fr_pdp_uses_french_terminology():
            return super()._get_peppol_checkbox_label(default_label)
        return self.env._("by the Approved Platform")

    def _get_peppol_checkbox_addendum_disable_reason(self):
        self.ensure_one()
        if self.l10n_fr_pdp_force_send_einvoicing:
            pdp_partner = self.move_id.partner_id.commercial_partner_id.with_company(self.company_id)
            if pdp_partner._l10n_fr_pdp_is_not_in_annuaire():
                if pdp_partner._l10n_fr_pdp_is_b2c():
                    return self.env._(" (No Siren/Siret)")
                if self.move_id.peppol_is_sent:
                    return self.env._(" (Previously sent)")
                return ""
        if self.move_id.peppol_is_sent:
            return super()._get_peppol_checkbox_addendum_disable_reason()
        pdp_partner = self.move_id.partner_id.commercial_partner_id.with_company(self.company_id)
        if pdp_partner._get_pdp_receiver_identification_info()[0] != 'pdp':
            if self.company_id._l10n_fr_pdp_uses_french_terminology() and pdp_partner.peppol_verification_state in ('not_valid', 'not_verified'):
                return self.env._(" (Customer not available for French E-Invoicing)")
            return super()._get_peppol_checkbox_addendum_disable_reason()
        partner_is_valid = pdp_partner.peppol_verification_state == 'valid'
        verification_display_state_map = dict(pdp_partner._fields['pdp_verification_display_state']._description_selection(self.env))
        reason = None
        if pdp_partner._l10n_fr_pdp_is_b2c():
            reason = self.env._("No Siren/Siret")
        if not partner_is_valid:
            reason = verification_display_state_map[pdp_partner.pdp_verification_display_state]
        if self.move_id.peppol_is_sent:
            reason = self.env._("Previously sent")
        if reason:
            return f" ({reason})"
        return ""

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------

    def _compute_sending_method_checkboxes(self):
        # EXTENDS 'account'
        for wizard in self:
            move = wizard.move_id
            partner = move.partner_id.commercial_partner_id

            if (
                not move or move.company_id._get_peppol_proxy_type() != 'pdp'
                or (partner.peppol_eas == '0225' and partner.peppol_endpoint)
                or not (siren := partner._l10n_fr_pdp_get_siren())
            ):
                continue

            lookup_result = self.env['res.partner']._fetch_active_annuaire_lines(siren)

            if identifiers := lookup_result.get('identifiers', []):
                if len(identifiers) == 1:
                    updated_identifier = identifiers[0]
                else:
                    id_type, id_value = partner._l10n_fr_pdp_get_base_identifier()
                    siren_siret = f"{siren}_{id_value}" if id_type == 'siret' else None

                    if siren_siret and (siren_siret_identifiers := [identifier for identifier in identifiers if identifier.startswith(siren_siret)]):
                        updated_identifier = min(siren_siret_identifiers, key=len)
                    elif siren in identifiers:
                        updated_identifier = siren
                    else:
                        updated_identifier = min(identifiers, key=len)

                partner.write({
                    'peppol_eas': '0225',
                    'peppol_endpoint': updated_identifier,
                    'invoice_edi_format': 'ubl_21_fr',
                })

        super()._compute_sending_method_checkboxes()

    def action_send_and_print(self, allow_fallback_pdf=False):
        self.ensure_one()
        if not self.l10n_fr_pdp_force_send_einvoicing:
            return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
        self = self.with_context(l10n_fr_pdp_force_send_einvoicing=True)
        if self.sending_methods and 'peppol' in self.sending_methods:
            move = self.move_id.with_company(self.move_id.company_id)
            if registration_action := self._do_peppol_pre_send(move):
                return registration_action
        # Skip the Peppol wizard guard that rejects a buyer who is not in the annuaire.
        return AccountMoveSendWizardAccount.action_send_and_print(self, allow_fallback_pdf=allow_fallback_pdf)
