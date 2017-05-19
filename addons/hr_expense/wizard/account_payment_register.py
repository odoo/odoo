# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import url_encode
from odoo import api, fields, models, _


class RegisterExpensePayment(models.TransientModel):
    _inherit = "account.payment.register"

    expense_sheet_id = fields.Many2one('hr.expense.sheet')

    @api.multi
    def get_payments_vals(self):
        if self.expense_sheet_id:
            return [self._prepare_expense_payment_vals(self.expense_sheet_id)]
        else:
            return super(RegisterExpensePayment, self).get_payments_vals()

    @api.multi
    def _compute_payment_amount_for_expense_sheet(self, expense_sheet, currency=None):
        """Compute the total amount for the payment wizard.

        :param hr.expense.sheet expense_sheet:
        :param currency: If not specified, search a default currency on journal.
        :return: The total amount to pay the expense.
        """
        if not currency:
            currency = self.journal_id.currency_id or self.journal_id.company_id.currency_id
        if expense_sheet.currency_id == currency:
            total = expense_sheet.total_amount
        else:
            total = expense_sheet.currency_id.with_context(date=self.payment_date).compute(expense_sheet.total_amount, currency)
        return total

    @api.multi
    def _prepare_expense_payment_vals(self, expense_sheet):
        partner = expense_sheet.address_id or expense_sheet.employee_id.address_home_id
        amount = self._compute_payment_amount_for_expense_sheet(expense_sheet)
        return {
            'journal_id': self.journal_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_date': self.payment_date,
            'communication': expense_sheet.name,
            'payment_type': 'outbound',
            'amount': abs(amount),
            'currency_id': expense_sheet.currency_id.id,
            'partner_id': partner.id,
            'partner_type': 'supplier',
            # partner_bank_id ?
        }

    def _reconcile_expense_payments(self):
        payment = self.payment_ids[0]
        # Log the payment in the chatter
        msg = _("A payment of %s %s with the reference <a href='/mail/view?%s'>%s</a> related to your expense <i>%s</i> has been made.")
        body = msg % (
            payment.amount,
            payment.currency_id.symbol,
            url_encode({'model': 'account.payment', 'res_id': payment.id}),
            payment.name,
            self.expense_sheet_id.name)
        self.expense_sheet_id.message_post(body=body)

        # Reconcile the payment and the expense, i.e. lookup on the payable account move lines
        account_move_lines_to_reconcile = self.env['account.move.line']
        for line in payment.move_line_ids + self.expense_sheet_id.account_move_id.line_ids:
            if line.account_id.internal_type == 'payable':
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.reconcile()
        return payment

    @api.multi
    def create_payments(self):
        res = super(RegisterExpensePayment, self).create_payments()
        if not self.expense_sheet_id:
            return res

        self._reconcile_expense_payments()
        # When expense is paid, unlike invoice payments, we do not want to open the Payment that was created, hence closing the payment wizard.
        return {'type': 'ir.actions.act_window_close'}
