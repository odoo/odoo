from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_pt_is_invoice_receipt(self):
        # A PoS invoice is posted before its payments are reconciled: it is an invoice-receipt when its
        # orders were paid at the till. A sale charged to the customer's account is not paid at issue.
        paid_orders = self.pos_order_ids.filtered(lambda o: o.state in ('paid', 'done'))
        return (
            super()._l10n_pt_is_invoice_receipt()
            or (
                self._l10n_pt_country_ok()
                and self.move_type == 'out_invoice'
                and paid_orders
                and 'pay_later' not in paid_orders.payment_ids.payment_method_id.mapped('type')
            )
        )
