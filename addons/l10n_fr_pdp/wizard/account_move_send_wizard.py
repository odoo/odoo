from odoo import _, models


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

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------

    def _compute_sending_method_checkboxes(self):
        # EXTENDS 'account'
        super()._compute_sending_method_checkboxes()

        checkboxes_to_recompute = self.env['account.move.send.wizard']
        multiple_lines_records = self.env['account.move.send.wizard']

        for wizard in self:
            move = wizard.move_id
            if not move or move.company_id.account_fiscal_country_id.code != 'FR':
                continue

            partner = move.partner_id.commercial_partner_id
            if partner.peppol_eas != '0225' and 'peppol' in wizard.sending_method_checkboxes:
                id_type, id_value = partner._l10n_fr_pdp_get_base_identifier()
                siren = id_value[:9] if id_type in ('siret', 'siren') else False
                is_multiple_lines = False

                if siren:
                    lookup_result = self.env['res.partner']._active_annuaire_registries(siren)

                    if lookup_result and lookup_result.get('in_annuaire'):
                        if lookup_result.get('count') == 1:
                            partner.write({
                                'peppol_eas': '0225',
                                'peppol_endpoint': lookup_result.get('identifiers')[0]
                            })
                            checkboxes_to_recompute |= wizard
                        elif lookup_result.get('count') > 1:
                            is_multiple_lines = True

                    else:
                        on_peppol = False
                        if partner.peppol_eas in ('9957', '0002', '0009') and partner.peppol_verification_state == 'valid':
                            on_peppol = True
                        elif partner.vat:
                            peppol_state = self.env['res.partner']._get_peppol_verification_state(
                                partner.vat,
                                '9957',
                                partner._get_peppol_edi_format()
                            )
                            if peppol_state == 'valid':
                                partner.write({
                                    'peppol_eas': '9957',
                                    'peppol_endpoint': partner.vat
                                })
                                on_peppol = True
                                checkboxes_to_recompute |= wizard

                        if not on_peppol:
                            partner.write({
                                'peppol_eas': '0225',
                                'peppol_endpoint': siren
                            })
                            checkboxes_to_recompute |= wizard

                # For a given SIREN, if more than one line exists on the annuaire, warn the user to go the partner's settings and choose
                # the correct identifier as there is no way to know which line belongs to the partner
                if is_multiple_lines:
                    multiple_lines_records |= wizard

        if checkboxes_to_recompute:
            super(AccountMoveSendWizard, checkboxes_to_recompute)._compute_sending_method_checkboxes()

        for wizard in multiple_lines_records:
            checkboxes = wizard.sending_method_checkboxes
            checkboxes['peppol'].update({
                'checked': False,
                'readonly': True,
                'disabled': True,
                'l10n_fr_ambiguous': True,
            })
            wizard.sending_method_checkboxes = checkboxes

    def _compute_alerts(self):
        # EXTENDS 'account'
        super()._compute_alerts()

        for wizard in self:
            peppol_box = (wizard.sending_method_checkboxes or {}).get('peppol', {})
            partner = wizard.move_id.partner_id.commercial_partner_id

            if peppol_box.get('l10n_fr_ambiguous'):
                new_alerts = wizard.alerts if wizard.alerts else {}

                new_alerts['l10n_fr_pdp_ambiguous_annuaire'] = {
                    'level': 'warning',
                    'message': _(
                        "Multiple active registrations were found in the French directory for %(partner)s. "
                        "Please select the correct e-invoicing identifier before sending.",
                        partner=partner.display_name
                    ),
                    'action_text': _("Open Partner Settings"),
                    'action': {
                        'type': 'ir.actions.act_url',
                        'url': f'/odoo/customers/{partner.id}',
                        'target': 'new',
                    }
                }
                wizard.alerts = new_alerts
