from odoo import fields, models


class AccountMoveTicarifaturaResponseWizard(models.TransientModel):
    _name = 'l10n_tr.ticarifatura.response.wizard'
    _description = 'Response Wizard for Bills of type Ticarifatura E-Invoice'

    move_id = fields.Many2one('account.move', required=True)
    response_code = fields.Selection([
        ('approved', "Approve"),
        ('rejected', "Reject"),
    ], string="Response Code", required=True)
    response_note = fields.Text(string="Response Note")

    def action_proceed(self):
        self.ensure_one()
        self.move_id._l10n_tr_action_send_ticarifatura_response(self.response_code, self.response_note or '')
        return {'type': 'ir.actions.act_window_close'}
