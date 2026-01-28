from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_qr_code_str(self):
        for order in self:
            if any(o._is_settle_or_deposit_order() for o in order.pos_order_ids):
                order.l10n_sa_qr_code_str = False
            else:
                super(AccountMove, order)._compute_qr_code_str()
