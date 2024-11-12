from odoo import _, fields, models


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    send_by_post_stamps = fields.Integer(compute='_compute_send_by_post_stamps')

    def _compute_send_by_post_stamps(self):
        for wizard in self:
            partner_with_valid_address = wizard.move_ids.partner_id.filtered(
                self.env['snailmail.letter']._is_valid_address
            )
            wizard.send_by_post_stamps = len(partner_with_valid_address)

    def _compute_summary_data(self):
        # EXTENDS 'account'
        super()._compute_summary_data()
        for wizard in self:
            if 'snailmail' in wizard.summary_data:
                wizard.summary_data['snailmail'].update({'extra': _('(Stamps: %s)', wizard.send_by_post_stamps)})
