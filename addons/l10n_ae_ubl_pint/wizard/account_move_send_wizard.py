from odoo import models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    def _compute_sending_method_checkboxes(self):
        """ Hide "by Peppol" for a document that isn't sent by Peppol. """
        # EXTENDS 'account_peppol'
        super()._compute_sending_method_checkboxes()
        for wizard in self:
            if 'peppol' in wizard.sending_method_checkboxes and not wizard.move_id._l10n_ae_is_sent_by_peppol():
                wizard.sending_method_checkboxes = {
                    method: values
                    for method, values in wizard.sending_method_checkboxes.items()
                    if method != 'peppol'
                }
