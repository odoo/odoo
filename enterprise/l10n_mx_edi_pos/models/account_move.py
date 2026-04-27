from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('origin_payment_id')
    def _compute_l10n_mx_edi_payment_method_id(self):
        super()._compute_l10n_mx_edi_payment_method_id()
        for move in self:
            if payment_method := move.origin_payment_id.pos_payment_method_id.l10n_mx_edi_payment_method_id:
                move.l10n_mx_edi_payment_method_id = payment_method
