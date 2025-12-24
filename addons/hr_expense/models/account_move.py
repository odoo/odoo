# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo import Command, models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import frozendict


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_ids = fields.One2many(comodel_name='hr.expense', inverse_name='account_move_id')
    nb_expenses = fields.Integer(compute='_compute_nb_expenses', string='Number of Expenses', compute_sudo=True)

    def _compute_nb_expenses(self):
        for move in self:
            move.nb_expenses = len(move.expense_ids)

    @api.depends('partner_id', 'expense_ids', 'company_id')
    def _compute_commercial_partner_id(self):
        own_expense_moves = self.filtered(lambda move: any(expense.payment_mode == 'own_account' for expense in move.sudo().expense_ids))
        for move in own_expense_moves:
            move.commercial_partner_id = (
                move.partner_id.commercial_partner_id
                if move.partner_id.commercial_partner_id != move.company_id.partner_id
                else move.partner_id
            )
        super(AccountMove, self - own_expense_moves)._compute_commercial_partner_id()

    @api.constrains('expense_ids')
    def _check_expense_ids(self):
        for move in self:
            expense_payment_modes = move.expense_ids.mapped('payment_mode')
            if 'company_account' in expense_payment_modes and len(move.expense_ids) > 1 :
                raise ValidationError(_("Each expense paid by the company must have a distinct and dedicated journal entry."))

    def action_open_expense(self):
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

    # Expenses can be written on journal other than purchase, hence don't include them in the constraint check
    def _check_journal_move_type(self):
        return super(AccountMove, self.filtered(lambda x: not x.expense_ids))._check_journal_move_type()

    def _creation_message(self):
        if self.expense_ids:
            if len(self.expense_ids) == 1:
                return _("Journal entry created from this expense: %(link)s", link=self.expense_ids._get_html_link())
            links = self.expense_ids[0]._get_html_link()
            for additional_expense in self.expense_ids[1:]:  # ', ' Destroys Markup, and each part here is safe
                links += ', ' + additional_expense._get_html_link()
            return _("Journal entry created from these expenses: %(links)s", links=links)
        return super()._creation_message()

    @api.depends('expense_ids')
    def _compute_needed_terms(self):
        # EXTENDS account
        # We want to set the account destination based on the 'payment_mode'.
        super()._compute_needed_terms()
        for move in self:
            if move.expense_ids and 'company_account' in move.expense_ids.mapped('payment_mode'):
                term_lines = move.line_ids.filtered(lambda l: l.display_type != 'payment_term')
                move.needed_terms = {
                    frozendict(
                        {
                            "move_id": move.id,
                            "date_maturity": fields.Date.context_today(move.expense_ids),
                        }
                    ): {
                        "balance": -sum(term_lines.mapped("balance")),
                        "amount_currency": -sum(term_lines.mapped("amount_currency")),
                        "name": move.payment_reference or "",
                        "account_id": move.expense_ids._get_expense_account_destination(),
                    }
                }

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        # EXTENDS 'account'
        results = super()._prepare_product_base_line_for_taxes_computation(product_line)
        if product_line.expense_id.payment_mode == 'own_account':
            results['special_mode'] = 'total_included'
        return results

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # EXTENDS account
        self.filtered('expense_ids').write({'expense_ids': [Command.clear()]})
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    def button_cancel(self):
        # EXTENDS account
        # We need to override this method to remove the link with the move, else we cannot reimburse them anymore.
        # And cancelling the move != cancelling the expense
        res = super().button_cancel()
        self.filtered('expense_ids').write({'expense_ids': [Command.clear()]})
        return res
