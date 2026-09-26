from odoo import models


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
