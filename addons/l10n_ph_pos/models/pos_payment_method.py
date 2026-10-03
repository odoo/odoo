# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, _, models
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_bank_payment_line_vals(self, session, amount, account=None, message=None, partner=None, foreign_currency=None, amount_currency=None, move=None):
        # EXTENDS point_of_sale
        payment_vals = super()._get_bank_payment_line_vals(session, amount, account, message, partner, foreign_currency, amount_currency, move=move)
        if (
            not move
            or foreign_currency
            or move.country_code != 'PH'
            or move.move_type != 'out_invoice'
            or move.currency_id != move.company_currency_id
            or move.currency_id.compare_amounts(amount, 0.0) <= 0
            or not move.withholding_total_amount_currency
        ):
            return payment_vals

        withholding_line_ids = self._l10n_ph_prepare_withholding_lines_commands(move, amount)
        if not withholding_line_ids:
            return payment_vals

        if not self.outstanding_account_id:
            raise UserError(_("Outstanding account is not set. Kindly set it up before proceeding with the transaction"))

        payment_vals.update({
            'withhold': 'withhold_pay',
            'withholding_line_ids': withholding_line_ids,
            'outstanding_account_id': self.outstanding_account_id.id,
            'invoice_ids': [Command.set(move.ids)],
        })
        return payment_vals

    def _l10n_ph_prepare_withholding_lines_commands(self, move, amount):
        """ Withhold and pay always: each bank payment of the move carries the share of its
        withholding taxes matching the share of the move it pays. The shares are computed from the
        cumulative amount paid so far (this payment included) by the bank payments of the move,
        so that their rounding always adds up to the full withholding once the move is fully paid
        by bank payments. The share paid in cash isn't withheld: there's no payment to carry it.
        """
        currency = move.currency_id
        base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
        withholding_line_ids = self.env['account.payment.withholding.line']._prepare_withholding_lines_commands(
            base_lines=base_lines,
            company=move.company_id,
        )

        previous_payments = self.env['account.payment'].search([
            ('invoice_ids', 'in', move.ids),
            ('pos_payment_method_id', '!=', False),
            ('withhold', '!=', 'payment'),
        ])
        paid_before = sum(previous_payments.mapped('amount'))
        ratio_before = min(paid_before / move.amount_total, 1.0)
        ratio_after = min((paid_before + amount) / move.amount_total, 1.0)

        def share(full_amount):
            return currency.round(full_amount * ratio_after) - currency.round(full_amount * ratio_before)

        commands = []
        for _command, _record_id, vals in withholding_line_ids:
            commands.append(Command.create({
                **vals,
                'source_base_amount_currency': share(vals['source_base_amount_currency']),
                'source_base_amount': share(vals['source_base_amount']),
                'source_tax_amount_currency': share(vals['source_tax_amount_currency']),
                'source_tax_amount': share(vals['source_tax_amount']),
            }))
        return commands
