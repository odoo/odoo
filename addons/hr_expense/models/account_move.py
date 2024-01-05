# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import escape

from odoo import Command, models, fields, api, _
from odoo.tools.misc import frozendict


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_sheet_id = fields.One2many('hr.expense.sheet', 'account_move_id')

    def action_open_expense_report(self):
        self.ensure_one()
        return {
            'name': self.expense_sheet_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'hr.expense.sheet',
            'res_id': self.expense_sheet_id.id
        }

    # Expenses can be written on journal other than purchase, hence don't include them in the constraint check
    def _check_journal_move_type(self):
        return super(AccountMove, self.filtered(lambda x: not x.expense_sheet_id))._check_journal_move_type()

    def _creation_message(self):
        if self.expense_sheet_id:
            return escape(_("Expense entry created from: %s")) % self.expense_sheet_id._get_html_link()
        return super()._creation_message()

    @api.depends('expense_sheet_id')
    def _compute_needed_terms(self):
        # EXTENDS account
        # We want to set the account destination based on the 'payment_mode'.
        super()._compute_needed_terms()
        for move in self:
            if move.expense_sheet_id and move.expense_sheet_id.payment_mode == 'company_account':
                term_lines = move.line_ids.filtered(lambda l: l.display_type != 'payment_term')
                move.needed_terms = {
                    frozendict(
                        {
                            "move_id": move.id,
                            "date_maturity": move.expense_sheet_id.accounting_date
                            or fields.Date.context_today(move.expense_sheet_id),
                        }
                    ): {
                        "balance": -sum(term_lines.mapped("balance")),
                        "amount_currency": -sum(term_lines.mapped("amount_currency")),
                        "name": "",
                        "account_id": move.expense_sheet_id._get_expense_account_destination(),
                    }
                }

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # Extends account
        # Reversing vendor bills that represent employee reimbursements should clear them from the expense sheet such that another
        # can be generated in place.
        own_account_moves = self.filtered(lambda move: move.expense_sheet_id.payment_mode == 'own_account')
        own_account_moves.write({
            'ref': False,  # else, when restarting the expense flow we get duplicate issue on vendor.bill
            'expense_sheet_id': [Command.clear()],  # There is no reversed state for employee expense
        })
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    def unlink(self):
        # EXTENDS account
        if self.expense_sheet_id:
            self.expense_sheet_id.state = 'approve'
        return super().unlink()

    def button_draft(self):
        # EXTENDS account
        employee_expense_sheets = self.expense_sheet_id.filtered(
            lambda expense_sheet: expense_sheet.payment_mode == 'own_account'
        )
        employee_expense_sheets.state = 'post'
        return super().button_draft()
