from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_datetime


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        if peppol_moves := self.move_ids.filtered(lambda m: 'peppol' in self._get_default_sending_methods(m)):
            remaining_quota, reset_at = self._peppol_fetch_remaining_quota()
            if remaining_quota < len(peppol_moves):
                if remaining_quota > 0:
                    raise UserError(_(
                        "You tried to send too many invoices at once. "
                        "You can still send %d more today through Peppol. "
                        "Your limit will reset on %s. "
                        "If you often need to send more, please contact our support team.",
                        remaining_quota,
                        format_datetime(self.env, reset_at),
                    ))
                else:
                    raise UserError(_(
                        "You've reached your daily Peppol sending limit. "
                        "You'll be able to send invoices again after %s. "
                        "If you often need a higher limit, please contact our support team.",
                        format_datetime(self.env, reset_at),
                    ))

            # If within quota, continue as usual
            registration_action = self._do_peppol_pre_send(peppol_moves)
            if registration_action:
                return registration_action

            if registration_action := self._do_peppol_pre_send(peppol_moves):
                return registration_action
        return super().action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf)
