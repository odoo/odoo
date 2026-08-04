from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_pt_is_invoice_receipt(self):
        return (
            super()._l10n_pt_is_invoice_receipt()
            or (
                self._l10n_pt_country_ok()
                and self.move_type == 'out_invoice'
                and self.pos_order_ids.filtered(lambda o: o.state in ('paid', 'done', 'invoiced'))
            )
        )
