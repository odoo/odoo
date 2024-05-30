# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.api import ondelete
from odoo.exceptions import UserError
from odoo.tools.misc import frozendict


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_sheet_id = fields.Many2one(comodel_name='hr.expense.sheet', ondelete='set null', copy=False, index='btree_not_null')
    show_commercial_partner_warning = fields.Boolean(compute='_compute_show_commercial_partner_warning')

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
        return super(AccountMove, self.filtered(lambda x: not x.expense_sheet_id))._check_journal_move_type()

    def _creation_message(self):
        if self.expense_sheet_id:
            return _("Expense entry created from: %s", self.expense_sheet_id._get_html_link())
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
                            "date_maturity": move.expense_sheet_id.accounting_date or fields.Date.context_today(move.expense_sheet_id),
                        }
                    ): {
                        "balance": -sum(term_lines.mapped("balance")),
                        "amount_currency": -sum(term_lines.mapped("amount_currency")),
                        "name": "",
                        "account_id": move.expense_sheet_id._get_expense_account_destination(),
                    }
                }

    def _reverse_moves(self, default_values_list=None, cancel=False):
        own_expense_moves = self.filtered(lambda move: move.expense_sheet_id.payment_mode == 'own_account')
        own_expense_moves.write({'expense_sheet_id': False, 'ref': False})
        # else, when restarting the expense flow we get duplicate issue on vendor.bill
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    @ondelete(at_uninstall=True)
    def _must_delete_all_expense_entries(self):
        if self.expense_sheet_id and self.expense_sheet_id.account_move_ids - self:  # If not all the payments are to be deleted
            raise UserError(_("You cannot delete only some entries linked to an expense report. All entries must be deleted at the same time."))
