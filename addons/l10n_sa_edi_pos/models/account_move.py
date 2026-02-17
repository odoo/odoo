from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_qr_code_str(self):
        for order in self:
            if any(o._is_settle_or_deposit_order() for o in order.pos_order_ids):
                order.l10n_sa_qr_code_str = False
            else:
                super(AccountMove, order)._compute_qr_code_str()

    def _move_has_settle_or_deposit_pos_order(self):
        """
            Check if the invoice is linked to a POS settlement order
            Only available when pos_settle_due module is installed
        """
        self.ensure_one()
        if not hasattr(self.env['pos.order.line'], '_is_settle_or_deposit'):
            return False
        return any(line._is_settle_or_deposit() for line in self.pos_order_ids.lines)
