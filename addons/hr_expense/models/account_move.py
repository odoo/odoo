# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import frozendict


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_ids = fields.One2many(comodel_name='hr.expense', inverse_name='account_move_id')
    show_commercial_partner_warning = fields.Boolean(compute='_compute_show_commercial_partner_warning')


    @api.constrains('expense_ids')
    def _check_expense_ids(self):
        for move in self:
            expense_payment_modes = move.expense_ids.mapped('payment_mode')
            if 'company_account' in expense_payment_modes and len(move.expense_ids) > 1 :
                raise ValidationError(_("Only one journal entry can be linked per expense, if the expense was paid by the company"))

    def action_open_expense_report(self):
        self.ensure_one()
        linked_expenses = self.expense_ids
        if len(linked_expenses) > 1:
            return {
            'name': _("Expenses"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'res_model': 'hr.expense',
            'domain': [('id', 'in', linked_expenses.ids)],
        }
        return {
            'name': linked_expenses.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'hr.expense',
            'res_id': linked_expenses.id
        }

    @api.depends('commercial_partner_id')
    def _compute_show_commercial_partner_warning(self):
        for move in self:
            move.show_commercial_partner_warning = (
                    move.commercial_partner_id == self.env.company.partner_id
                    and move.move_type == 'in_invoice'
                    and move.partner_id.employee_ids
            )

    # Expenses can be written on journal other than purchase, hence don't include them in the constraint check
    def _check_journal_move_type(self):
        return super(AccountMove, self.filtered(lambda x: not x.expense_ids))._check_journal_move_type()

    def _creation_message(self):
        if self.expense_ids:
            expense_links = (_("%(name)s: %(link)s", name=expense.name, link=expense._get_html_link()) for expense in self.expense_ids)
            return _("Expense entry created from: %(expense_links)s", expense_links='\n'.join(expense_links))
        return super()._creation_message()

    @api.depends('expense_ids')
    def _compute_needed_terms(self):
        # EXTENDS account
        # We want to set the account destination based on the 'payment_mode'.
        super()._compute_needed_terms()
        for move in self:
            if move.expense_ids and move.expense_ids.payment_mode == 'company_account':
                term_lines = move.line_ids.filtered(lambda l: l.display_type != 'payment_term')
                move.needed_terms = {
                    frozendict(
                        {
                            "move_id": move.id,
                            "date_maturity": move.expense_ids.accounting_date or fields.Date.context_today(move.expense_ids),
                        }
                    ): {
                        "balance": -sum(term_lines.mapped("balance")),
                        "amount_currency": -sum(term_lines.mapped("amount_currency")),
                        "name": "",
                        "account_id": move.expense_ids._get_expense_account_destination(),
                    }
                }

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        # EXTENDS 'account'
        results = super()._prepare_product_base_line_for_taxes_computation(product_line)
        if product_line.expense_id:
            results['special_mode'] = 'total_included'
        return results

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # EXTENDS account
        own_expense_moves = self.filtered(lambda move: move.expense_ids.payment_mode == 'own_account')
        own_expense_moves.write({'expense_ids': False, 'ref': False})
        # else, when restarting the expense flow we get duplicate issue on vendor.bill
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    def button_cancel(self):
        # EXTENDS account
        # We need to override this method to remove the link with the move, else we cannot reimburse them anymore.
        # And cancelling the move != cancelling the expense
        res = super().button_cancel()
        self.write({'expense_ids': False, 'ref': False})
        return res
