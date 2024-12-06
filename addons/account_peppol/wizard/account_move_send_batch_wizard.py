from odoo import api,models


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    @api.model
    def _get_default_sending_method(self, move) -> set:
        """ By default, we use the sending method set on the partner or email and peppol. """
        return set([move.partner_id.with_company(move.company_id).invoice_sending_method] or ['email', 'peppol'])

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        if peppol_moves := self.move_ids.filtered(lambda m: 'peppol' in self._get_default_sending_method(m)):
            if registration_action := self._do_peppol_pre_send(peppol_moves):
                return registration_action
        return super().action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf)
