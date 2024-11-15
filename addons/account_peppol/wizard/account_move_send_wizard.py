# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _compute_sending_method_checkboxes(self):
        # EXTENDS 'account': if Customer is not valid on Peppol, we disable the checkbox
        super()._compute_sending_method_checkboxes()
        for wizard in self:
            peppol_partner = wizard.move_id.partner_id.commercial_partner_id.with_company(wizard.company_id)
            peppol_partner.button_account_peppol_check_partner_endpoint(company=wizard.company_id)
            if peppol_partner.peppol_verification_state == 'not_valid' \
                and (peppol_checkbox := wizard.sending_method_checkboxes.get('peppol')):
                wizard.sending_method_checkboxes = {
                    **wizard.sending_method_checkboxes,
                    'peppol': {
                        'label': _('%s (customer not on Peppol)', peppol_checkbox['label']),
                        'readonly': True,
                        'checked': False,
                    }
                }

    def action_send_and_print(self, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        if self.sending_methods and 'peppol' in self.sending_methods:
            if registration_action := self._do_peppol_pre_send(self.move_id):
                return registration_action
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
