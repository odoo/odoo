from odoo import models


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        self.move_ids.filtered(lambda m: self._get_default_sending_methods(m) == 'nemhandel').nemhandel_move_state = 'to_send'
        return super().action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf)
