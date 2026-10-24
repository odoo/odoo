from odoo import _, fields, models


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    send_by_post_stamps = fields.Integer(compute='_compute_send_by_post_stamps')

    def _compute_send_by_post_stamps(self):
        for wizard in self:
            stamps = 0
            # One letter is created per move (see _hook_if_success), and the IAP service
            # charges one stamp per document, whatever its number of physical pages.
            for move in wizard.move_ids:
                sending_settings = self._get_default_sending_settings(move)
                if (
                    'snailmail' in sending_settings['sending_methods']
                    and self._is_applicable_to_move('snailmail', move, **sending_settings)
                ):
                    stamps += 1
            wizard.send_by_post_stamps = stamps

    def _compute_summary_data(self):
        # EXTENDS 'account'
        super()._compute_summary_data()
        for wizard in self:
            if wizard.summary_data and 'snailmail' in wizard.summary_data:
                wizard.summary_data['snailmail'].update({'extra': _('(Stamps: %s)', wizard.send_by_post_stamps)})
