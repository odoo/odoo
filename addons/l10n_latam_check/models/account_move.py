# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        super().button_draft()
        for move in self.filtered(lambda x: x.origin_payment_id.payment_method_code == 'own_checks'):
            move.origin_payment_id._l10n_latam_check_unlink_split_move()
