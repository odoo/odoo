from odoo import models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _compute_state(self):
        # When a payment is created from a transaction linked to a sales order,
        # we want to keep it in the 'in_process' state
        # until all related invoices are fully paid.
        # Example: Sales order with one line and a quantity of 2.
        # - First invoice with a quantity of 1: the invoice is fully paid,
        #   but the payment state must remain 'in_process'.
        # - Second invoice with a quantity of 1: the invoice is fully paid,
        #   and the payment state can be set to 'paid'.
        res = super()._compute_state()
        for payment in self.filtered(
            lambda payment: payment.state == 'paid'
            and payment.move_id
            and payment.payment_transaction_id.sale_order_ids
        ):
            _liquidity, counterpart_lines, _writeoff = payment._seek_for_lines()
            residual_amount = sum(counterpart_lines.mapped('amount_residual'))
            has_residual = not payment.company_currency_id.is_zero(residual_amount)
            is_reconcile = any(counterpart_lines.account_id.mapped('reconcile'))
            if has_residual and is_reconcile:
                payment.state = 'in_process'
        return res
