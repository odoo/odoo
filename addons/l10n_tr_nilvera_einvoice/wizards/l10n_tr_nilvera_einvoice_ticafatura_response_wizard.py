from odoo import fields, models


class AccountMoveTicafaturaResponseWizard(models.TransientModel):
    _name = 'l10n_tr.ticafatura.response.wizard'
    _description = 'Response Wizard for Bills of type Ticafatura E-Invoice'

    move_id = fields.Many2one('account.move', required=True)
    response_code = fields.Selection([
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
    ], string='Response Code', required=True)
    response_note = fields.Text(string='Response Note')

    def action_proceed(self):
        self.ensure_one()
        if self.response_code == 'approved':
            self.move_id.l10n_tr_action_send_ticarifatura_response('approved')
        else:
            self.move_id.l10n_tr_action_send_ticarifatura_response('rejected', self.response_note)

        return {'type': 'ir.actions.act_window_close'}
