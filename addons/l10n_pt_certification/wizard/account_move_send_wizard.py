import json

from odoo import models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    def action_send_and_print(self, allow_fallback_pdf=False):
        # EXTENDS account - trigger reprint wizard if needed
        self.ensure_one()
        if (
                self.move_id.country_code == 'PT'
                and self.move_id.move_type in ('out_invoice', 'out_refund', 'out_receipt')
                and self.move_id.l10n_pt_print_version
                and not self.env.context.get('has_reprint_reason')
        ):
            return self.action_open_reprint_wizard()
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)

    def action_open_reprint_wizard(self):
        action = self.env.ref('l10n_pt_certification.action_open_reprint_wizard').read()[0]
        action['context'] = dict(action_to_return='action_send_and_print', **json.loads(action.get('context', {})))
        return action
