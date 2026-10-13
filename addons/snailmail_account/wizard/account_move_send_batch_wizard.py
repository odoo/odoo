from odoo import _, models


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    def _compute_summary_data(self):
        # EXTENDS 'account'
        super()._compute_summary_data()
        for wizard in self:
            # Json fields return a copy of their value, so the summary has to be
            # assigned back instead of being updated in place.
            summary_data = wizard.summary_data
            if summary_data and 'snailmail' in summary_data:
                # One letter is created per invoice sent by post (see _hook_if_success)
                # and the IAP service charges one stamp per letter.
                summary_data['snailmail']['extra'] = _('(Stamps: %s)', summary_data['snailmail']['count'])
                wizard.summary_data = summary_data
