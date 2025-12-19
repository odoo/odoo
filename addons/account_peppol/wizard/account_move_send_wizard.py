# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.exceptions import UserError

class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _get_peppol_checkbox_label(self, default_label):
        return default_label

    def _get_peppol_checkbox_addendum_disable_reason(self):
        self.ensure_one()
        peppol_partner = self.move_id.partner_id.commercial_partner_id.with_company(self.company_id)
        if peppol_partner.peppol_verification_state == 'not_valid':
            return self.env._(' (Customer not on Peppol)')
        elif peppol_partner.peppol_verification_state == 'not_verified':
            # The recomputation of the Peppol credentials did not manage to fill these fields.
            if not peppol_partner.peppol_eas or not peppol_partner.peppol_endpoint:
                eas_label = dict(peppol_partner._fields['peppol_eas']._description_selection(self.env)).get(peppol_partner.peppol_eas)
                if not peppol_partner.vat:
                    return _(' (no VAT)')
                elif eas_label:
                    return _(' (Missing %(eas)s)', eas=eas_label)
            return _(' (Customer not on Peppol)')
        else:
            return ''

    def _compute_sending_method_checkboxes(self):
        """ EXTENDS 'account'
        If Customer is not valid on Peppol, we disable the checkbox. Also add the proxy mode if not in prod.
        """
        for wizard in self:
            peppol_partner = wizard.move_id.partner_id.commercial_partner_id.with_company(wizard.company_id)
            if not peppol_partner.peppol_eas or not peppol_partner.peppol_endpoint:
                peppol_partner._compute_peppol_endpoint()  # Try to recompute the Peppol credentials.
            peppol_partner.button_account_peppol_check_partner_endpoint(company=wizard.company_id)
        super()._compute_sending_method_checkboxes()
        for wizard in self:
            if peppol_checkbox := wizard.sending_method_checkboxes.get('peppol'):
                peppol_proxy_mode = wizard.company_id._get_peppol_edi_mode()
                peppol_label = wizard._get_peppol_checkbox_label(peppol_checkbox['label'])
                addendum_disable_reason = wizard._get_peppol_checkbox_addendum_disable_reason()
                vals_not_valid = {'readonly': True, 'checked': False} if addendum_disable_reason else {}
                addendum_mode = ''
                if peppol_proxy_mode == 'test':
                    addendum_mode = _(' (Test)')
                elif peppol_proxy_mode == 'demo':
                    addendum_mode = _(' (Demo)')
                if addendum_disable_reason or addendum_mode:
                    wizard.sending_method_checkboxes = {
                        **wizard.sending_method_checkboxes,
                        'peppol': {
                            **peppol_checkbox,
                            **vals_not_valid,
                            'label': _(
                                '%(peppol_label)s%(disable_reason)s%(peppol_proxy_mode)s',
                                peppol_label=peppol_label,
                                disable_reason=addendum_disable_reason,
                                peppol_proxy_mode=addendum_mode,
                            ),
                        }
                    }

    def action_send_and_print(self, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        if self.sending_methods and 'peppol' in self.sending_methods:
            move = self.move_id.with_company(self.move_id.company_id)
            if move.partner_id.commercial_partner_id.peppol_verification_state != 'valid':
                raise UserError(_("Partner doesn't have a valid Peppol configuration."))
            if registration_action := self._do_peppol_pre_send(move):
                return registration_action
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
