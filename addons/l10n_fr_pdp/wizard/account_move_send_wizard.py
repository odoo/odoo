from odoo import api, models


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

        multiple_lines_records = self.env['account.move.send.wizard']

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
            if line_count := lookup_result.get('count', 0):
                if line_count == 1:
                    partner.write({
                        'peppol_eas': '0225',
                        'peppol_endpoint': lookup_result.get('identifiers')[0],
                    })
                elif line_count > 1:
                    multiple_lines_records |= wizard

        super()._compute_sending_method_checkboxes()

        # For a given SIREN, if more than one line exists on the annuaire, warn the user to go the partner's settings and choose
        # the correct identifier as there is no way to know which line belongs to the partner, and disable the checkbox to send via peppol
        for wizard in multiple_lines_records:
            checkboxes = wizard.sending_method_checkboxes
            if 'peppol' in checkboxes:
                checkboxes['peppol'].update({
                    'checked': False,
                    'readonly': True,
                    'disabled': True,
                    'l10n_fr_pdp_ambiguous': True,
                })
                wizard.sending_method_checkboxes = checkboxes

    @api.depends('sending_method_checkboxes')
    def _compute_alerts(self):
        # EXTENDS 'account'
        super()._compute_alerts()

        for wizard in self:
            peppol_box = (wizard.sending_method_checkboxes or {}).get('peppol', {})
            partner = wizard.move_id.partner_id.commercial_partner_id

            if peppol_box.get('l10n_fr_pdp_ambiguous'):
                new_alerts = wizard.alerts if wizard.alerts else {}

                new_alerts['l10n_fr_pdp_ambiguous_annuaire'] = {
                    'level': 'warning',
                    'message': self.env._(
                        "Multiple active registrations were found in the French directory for %(partner)s. "
                        "Please select the correct e-invoicing identifier before sending.",
                        partner=partner.display_name
                    ),
                    'action_text': self.env._("Open Partner Settings"),
                    'action': partner._get_records_action(),
                }
                wizard.alerts = new_alerts
