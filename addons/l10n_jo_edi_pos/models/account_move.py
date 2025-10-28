from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_l10n_jo_edi_is_needed(self):
        super()._compute_l10n_jo_edi_is_needed()
        # moves linked to pos.orders should be synchronized through the pos.order
        for move in self.filtered(lambda m: m.l10n_jo_edi_is_needed and m.pos_order_ids):
            move.l10n_jo_edi_is_needed = False
