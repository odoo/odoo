# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move = False
        if 'move_id' in res or (self.env.context.get('active_model') == 'account.move' and self.env.context.get('active_ids')):
            move = self.env['account.move'].browse(res.get('move_id') or self.env.context.get('active_ids'))
            partner = move.partner_id.commercial_partner_id
            partner.button_account_peppol_check_partner_endpoint(company=move.company_id)
        return res

    def _compute_sending_method_checkboxes(self):
        """ EXTENDS 'account'
        If Customer is not valid on Peppol, we disable the checkbox. Also add the proxy mode if not in prod.
        """
        super()._compute_sending_method_checkboxes()
        for wizard in self:
            peppol_partner = wizard.move_id.partner_id.commercial_partner_id.with_company(wizard.company_id)
            if peppol_checkbox := wizard.sending_method_checkboxes.get('peppol'):
                peppol_proxy_mode = wizard.company_id._get_peppol_edi_mode()
                addendum_not_valid = _(' (customer not on Peppol)') if peppol_partner.peppol_verification_state == 'not_valid' else ''
                vals_not_valid = {'readonly': True, 'checked': False} if addendum_not_valid else {}
                addendum_mode = _(' (Demo/Test mode)') if peppol_proxy_mode != 'prod' else ''
                if addendum_not_valid or addendum_mode:
                    wizard.sending_method_checkboxes = {
                        **wizard.sending_method_checkboxes,
                        'peppol': {
                            **peppol_checkbox,
                            **vals_not_valid,
                            'label': _(
                                '%(peppol_label)s%(not_valid)s%(peppol_proxy_mode)s',
                                peppol_label=peppol_checkbox['label'],
                                not_valid=addendum_not_valid,
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
                wizard.invoice_edi_format = 'ubl_bis3'
            elif wizard.invoice_edi_format != self._get_default_invoice_edi_format(wizard.move_id) and wizard.sending_methods and 'peppol' not in wizard.sending_methods:
                wizard.invoice_edi_format = None

    def action_send_and_print(self, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        if self.sending_methods and 'peppol' in self.sending_methods:
            if registration_action := self._do_peppol_pre_send(self.move_id):
                return registration_action
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
