# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ExpenseReturnCash(models.TransientModel):
    _name = 'od19.expense.return.cash'
    _description = 'Return Expense Cash'

    expense_id = fields.Many2one(
        'hr.expense',
        string='Expense / ค่าใช้จ่าย',
        required=True,
        readonly=True,
    )
    amount = fields.Monetary(
        string='Amount / จำนวนเงิน',
        currency_field='currency_id',
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='expense_id.currency_id',
        readonly=True,
    )
    return_date = fields.Date(
        string='Return Date / วันที่คืนเงิน',
        required=True,
        default=fields.Date.context_today,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal / สมุด',
        domain="[('type', 'in', ('cash', 'bank'))]",
        help='Journal where the returned cash is deposited.',
    )
    create_accounting_entry = fields.Boolean(
        string='Create Accounting Entry / สร้างผังรายการ',
        default=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_expense_id'):
            expense = self.env['hr.expense'].browse(
                self.env.context['default_expense_id']
            )
            if expense:
                res['expense_id'] = expense.id
                res['amount'] = expense.total_amount
        return res

    @api.constrains('amount')
    def _check_amount(self):
        for wizard in self:
            if wizard.amount <= 0:
                raise ValidationError(_('Return amount must be greater than zero.'))

    def action_return_cash(self):
        self.ensure_one()
        if not self.expense_id:
            raise UserError(_('Expense is missing.'))
        if self.expense_id.od19_cash_state not in ('received', 'used'):
            raise UserError(_(
                'Cash can only be returned when state is "Received" or "Used".'
            ))

        if self.create_accounting_entry:
            self._create_return_move()

        self.expense_id.od19_cash_state = 'returned'
        return {'type': 'ir.actions.act_window_close'}

    def _create_return_move(self):
        """Create a journal entry recording the cash return."""
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_(
                'Please select a journal to record the cash return.'
            ))
        expense = self.expense_id
        company_currency = expense.company_id.currency_id
        amount = self.amount
        balance = expense.currency_id._convert(
            amount, company_currency, expense.company_id, self.return_date
        )

        # Determine the accounts:
        # Debit: cash/bank account (money comes back)
        # Credit: the employee's payable account so the return can be matched
        # (reconciled) against the cash advance given to the employee.
        debit_account = self.journal_id.default_account_id
        employee_partner = (
            expense.employee_id.work_contact_id
            or expense.employee_id.user_id.partner_id
        )
        credit_account = expense.account_id
        if employee_partner:
            payable_account = (
                employee_partner.with_company(expense.company_id)
                .property_account_payable_id
            )
            if payable_account:
                credit_account = payable_account
        if not credit_account:
            credit_account = debit_account

        move_vals = {
            'date': self.return_date,
            'journal_id': self.journal_id.id,
            'ref': _('Cash Return - %s') % expense.name,
            'line_ids': [
                (0, 0, {
                    'name': _('Cash Return - %s') % expense.name,
                    'account_id': debit_account.id,
                    'partner_id': employee_partner.id or False,
                    'currency_id': expense.currency_id.id,
                    'amount_currency': amount,
                    'debit': balance if balance > 0 else 0.0,
                    'credit': -balance if balance < 0 else 0.0,
                    'date_maturity': self.return_date,
                }),
                (0, 0, {
                    'name': _('Cash Return - %s') % expense.name,
                    'account_id': credit_account.id,
                    'partner_id': employee_partner.id or False,
                    'currency_id': expense.currency_id.id,
                    'amount_currency': -amount,
                    'debit': -balance if balance < 0 else 0.0,
                    'credit': balance if balance > 0 else 0.0,
                    'date_maturity': self.return_date,
                }),
            ],
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        move._od19_reconcile_account_lines(
            credit_account.id, employee_partner.id or None
        )
        return move
