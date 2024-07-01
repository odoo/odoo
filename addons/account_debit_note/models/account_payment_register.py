# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _get_lpc_note_default_values(self, move):
        default_values = super()._get_lpc_note_default_values(move)
        default_values['debit_origin_id'] = move.id
        return default_values
