from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_sa_check_refund_reason(self):
        return super()._l10n_sa_check_refund_reason() or (self.pos_order_ids and self.pos_order_ids[0].refunded_orders_count > 0 and self.ref)

    def _compute_qr_code_str(self):
        for order in self:
            if any(o._is_settle_or_deposit_order() for o in order.pos_order_ids):
                order.l10n_sa_qr_code_str = False
            else:
                super(AccountMove, order)._compute_qr_code_str()
