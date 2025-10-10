from odoo import models


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    def _compute_summary_data(self):
        # EXTENDS 'account' - add checking of partner's validity
        for wizard in self:
            for move in wizard.move_ids.filtered(lambda m: wizard._get_default_sending_method(m) == 'nemhandel'):
                move.commercial_partner_id.button_nemhandel_check_partner_endpoint(company=move.company_id)
        super()._compute_summary_data()

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        self.move_ids.filtered(lambda m: self._get_default_sending_method(m) == 'nemhandel').nemhandel_move_state = 'to_send'
        return super().action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf)
