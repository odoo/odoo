# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_bank_payment_line_vals(self, session, amount, account=None, message=None, partner=None, foreign_currency=None, amount_currency=None, move=None):
        # EXTENDS point_of_sale
        payment_vals = super()._get_bank_payment_line_vals(session, amount, account, message, partner, foreign_currency, amount_currency, move=move)

        if not move or foreign_currency or not move.withholding_residual_amount_currency:
            return payment_vals

        withhold = self.env['account.payment.register']._get_default_withhold(move)
        if withhold == 'payment':
            return payment_vals

        # The withholding engine's "withhold and pay" mode isn't prorate-aware (it always books
        # the full withholding amount regardless of the payment amount), so it can only be
        # recognized when a single payment fully settles the move: splitting a withholding-taxed
        # order across several payment methods, or several orders sharing one session-closing
        # receipt, would double-count it. Skipping it here matches today's (silent) gap rather
        # than blocking an otherwise-normal POS flow.
        if float_compare(abs(amount), move.amount_residual, precision_rounding=move.currency_id.rounding) != 0:
            return payment_vals

        if not self.outstanding_account_id:
            raise UserError(_("Outstanding account is not set. Kindly set it up before proceeding with the transaction"))

        base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
        withholding_line_ids = self.env['account.payment.withholding.line']._prepare_withholding_lines_commands(
            base_lines=base_lines,
            company=self.company_id,
        )
        if not withholding_line_ids:
            return payment_vals

        payment_vals['withhold'] = withhold
        payment_vals['withholding_line_ids'] = withholding_line_ids
        payment_vals['outstanding_account_id'] = self.outstanding_account_id.id
        return payment_vals
