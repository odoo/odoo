# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _
from odoo.exceptions import UserError

class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _compute_sending_method_checkboxes(self):
        """ EXTENDS 'account'
        If Customer is not valid on Peppol, we disable the checkbox. Also add the proxy mode if not in prod.
        """
        for wizard in self:
            peppol_partner = wizard.move_id.partner_id.commercial_partner_id.with_company(wizard.company_id)
            peppol_partner.button_account_peppol_check_partner_endpoint(company=wizard.company_id)
        super()._compute_sending_method_checkboxes()
        for wizard in self:
            if peppol_checkbox := wizard.sending_method_checkboxes.get('peppol'):
                peppol_partner = wizard.move_id.partner_id.commercial_partner_id.with_company(wizard.company_id)
                peppol_proxy_mode = wizard.company_id._get_peppol_edi_mode()
                if peppol_partner.peppol_verification_state == 'not_valid':
                    addendum_disable_reason = _(' (Customer not on Peppol)')
                elif peppol_partner.peppol_verification_state == 'not_verified':
                    addendum_disable_reason = _(' (no VAT)')
                else:
                    addendum_disable_reason = ''
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
                                peppol_label=peppol_checkbox['label'],
                                disable_reason=addendum_disable_reason,
                                peppol_proxy_mode=addendum_mode,
                            ),
                        }
                    }

    @api.depends('sending_methods')
    def _compute_invoice_edi_format(self):
        # EXTENDS 'account' - add default on bis3 if not set on partner's preferences and "by Peppol" is selected
        super()._compute_invoice_edi_format()
        for wizard in self:
            if not wizard.invoice_edi_format and wizard.sending_methods and 'peppol' in wizard.sending_methods:
                wizard.invoice_edi_format = wizard.move_id.partner_id._get_peppol_edi_format()
            elif wizard.invoice_edi_format != self._get_default_invoice_edi_format(wizard.move_id) and wizard.sending_methods and 'peppol' not in wizard.sending_methods:
                wizard.invoice_edi_format = None  # back to initial state if user unchecked 'by Peppol'

    def action_send_and_print(self, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        if self.sending_methods and 'peppol' in self.sending_methods:
            if self.move_id.partner_id.commercial_partner_id.peppol_verification_state != 'valid':
                raise UserError(_("Partner doesn't have a valid Peppol configuration."))
            if registration_action := self._do_peppol_pre_send(self.move_id):
                return registration_action
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
