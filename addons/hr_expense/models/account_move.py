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

    def is_entry(self):
        if self.expense_sheet_id:
            return False
        return super().is_entry()

    # Expenses can be written on journal other than purchase, hence don't include them in the constraint check
    def _check_journal_move_type(self):
        return super(AccountMove, self.filtered(lambda x: not x.expense_sheet_id))._check_journal_move_type()

    def _creation_message(self):
        if self.expense_sheet_id:
            return _("Expense entry Created")
        return super()._creation_message()

    @api.depends('expense_sheet_id.payment_mode')
    def _compute_payment_state(self):
        company_paid = self.filtered(lambda m: m.expense_sheet_id.payment_mode == 'company_account')
        for move in company_paid:
            move.payment_state = 'paid'
        super(AccountMove, self - company_paid)._compute_payment_state()

    @api.depends('expense_sheet_id')
    def _compute_needed_terms(self):
        # EXTENDS account
        # We want to set the account destination based on the 'payment_mode'.
        # Also, expense' account moves are expressed in the company currency.
        super()._compute_needed_terms()
        for move in self:
            if move.expense_sheet_id:
                amount_currency = -sum(move.line_ids.filtered(lambda l: l.display_type != 'payment_term').mapped("amount_currency"))
                move.needed_terms = {
                    frozendict(
                        {
                            "move_id": move.id,
                            "date_maturity": move.expense_sheet_id.accounting_date
                            or fields.Date.context_today(move.expense_sheet_id),
                        }
                    ): {
                        "balance": amount_currency,
                        "amount_currency": amount_currency,
                        "name": "",
                        "account_id": move.expense_sheet_id.expense_line_ids[0]._get_expense_account_destination(),
                    }
                }

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if self.expense_sheet_id:
            self.expense_sheet_id.state = 'approve'
            self.expense_sheet_id = False
            self.ref = False # else, when restarting the expense flow we get duplicate issue on vendor.bill
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    def unlink(self):
        if self.expense_sheet_id:
            self.expense_sheet_id.state = 'approve'
            self.expense_sheet_id.account_move_id = False # cannot change to delete='set null' in stable
        return super().unlink()

    def button_draft(self):
        for line in self.line_ids:
            if line.expense_id:
                line.expense_id.sheet_id.write({'state': 'post'})
        return super().button_draft()
