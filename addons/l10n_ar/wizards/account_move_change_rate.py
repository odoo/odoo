from odoo import fields, models, api, _


class AccountMoveChangeRate(models.TransientModel):
    _name = 'account.move.change.rate'
    _description = 'account.move.change.rate'

    @api.model
    def get_move(self):
        move = self.env['account.move'].browse(
            self._context.get('active_id', False))
        return move

    currency_rate = fields.Float(
        'Currency Rate',
        required=True,
        digits=(16, 6),
        help="Select a rate to apply on the invoice"
    )
    move_id = fields.Many2one(
        'account.move',
        default=get_move
    )

    @api.onchange('move_id')
    def _onchange_move(self):
        self.currency_rate = self.move_id.l10n_ar_currency_rate or self.move_id.l10n_ar_computed_currency_rate

    def confirm(self):
        message = _("Currency rate changed from %s to %s") % (self.currency_rate, self.currency_rate)
        self.move_id.message_post(body=message)
        self.move_id.l10n_ar_currency_rate = self.currency_rate
        return {'type': 'ir.actions.act_window_close'}
