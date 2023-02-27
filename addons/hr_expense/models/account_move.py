# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields, api, _
from odoo.tools.misc import frozendict


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_sheet_id = fields.One2many('hr.expense.sheet', 'account_move_id')

    def action_open_expense_report(self):
        self.ensure_one()
        return {
            'name': self.expense_sheet_id.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'res_id': self.expense_sheet_id.id
        }

    # Behave exactly like a receipt for everything except the display
    # This enables the synchronisation of payment terms, and sets the taxes and accounts based on the product
    def is_purchase_document(self, include_receipts=False):
        return bool(include_receipts and self.sudo().expense_sheet_id) or super().is_purchase_document(include_receipts)

    # Expenses can be written on journal other than purchase, hence don't include them in the constraint check
    def _check_journal_move_type(self):
        return super(AccountMove, self.filtered(lambda x: not x.expense_sheet_id))._check_journal_move_type()

    def _creation_message(self):
        if self.line_ids.expense_id:
            return _("Expense entry Created")
        return super()._creation_message()

    @api.depends('expense_sheet_id.payment_mode')
    def _compute_payment_state(self):
        company_paid = self.filtered(lambda m: m.expense_sheet_id.payment_mode == 'company_account')
        for move in company_paid:
            move.payment_state = move._get_invoice_in_payment_state()
        super(AccountMove, self - company_paid)._compute_payment_state()

    @api.depends('expense_sheet_id')
    def _compute_needed_terms(self):
        # EXTENDS account
        # The needed terms need to be computed for journal entries, depending on the expense and the currency
        # since one expense sheet can contain multiple currencies.
        super()._compute_needed_terms()
        for move in self:
            if move.expense_sheet_id:
                move.needed_terms = {}
                agg = defaultdict(lambda: {'company': 0.0, 'foreign': 0.0})
                for line in move.line_ids:
                    if line.display_type != 'payment_term':
                        agg[line.expense_id]['company'] += line.balance
                        agg[line.expense_id]['foreign'] += line.amount_currency
                for expense in move.line_ids.expense_id:
                    move.needed_terms[frozendict({
                        'move_id': move.id,
                        'date_maturity': expense.sheet_id.accounting_date or expense.date or fields.Date.context_today(expense),
                        'expense_id': expense.id,
                    })] = {
                        'balance': -agg[expense]['company'],
                        'amount_currency': -agg[expense]['foreign'],
                        'name': '',
                        'currency_id': expense.currency_id.id,
                        'account_id': expense._get_expense_account_destination(),
                    }
