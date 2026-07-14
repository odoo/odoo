from odoo import models
from odoo.exceptions import UserError


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    def action_send_and_print(self, allow_fallback_pdf=False):
        # EXTENDS account - prevent Send & Print if KE invoices aren't validated and no fallback is allowed.
        self.ensure_one()
        if not allow_fallback_pdf:
            if warning_moves := self._get_l10n_ke_edi_tremol_warning_moves(self.move_id):
                raise UserError(self._get_l10n_ke_edi_tremol_warning_message(warning_moves))
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
