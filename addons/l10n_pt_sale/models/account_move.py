from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_pt_is_invoice_receipt(self):
        return (
            super()._l10n_pt_is_invoice_receipt()
            or (
                self._is_pt_move()
                and self.move_type == 'out_invoice'
                and self.line_ids.sale_line_ids.order_id.transaction_ids.filtered(lambda tx: tx.state == 'done')
            )
        )
