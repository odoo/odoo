# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountMoveCashBasis(models.Model):
    _inherit = 'account.move'

    tax_cash_basis_rec_id = fields.Many2one(
        'account.partial.reconcile',
        string='Tax Cash Basis Entry of',
        help="Technical field used to keep track of the tax cash basis reconciliation."
        "This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def create(self, vals):
        taxes = False
        if vals.get('tax_line_id'):
            taxes = [{'use_cash_basis': self.env['account.tax'].browse(vals['tax_line_id']).use_cash_basis}]
        if vals.get('tax_ids'):
            taxes = self.env['account.move.line'].resolve_2many_commands('tax_ids', vals['tax_ids'])
        if taxes and any([tax['use_cash_basis'] for tax in taxes]) and not vals.get('tax_exigible'):
            vals['tax_exigible'] = False
        return super(AccountMoveLine, self).create(vals)

    def _get_matched_percentage(self):
        """ This function returns a dictionary giving for each move_id of self, the percentage to consider as cash basis factor.
        This is actuallty computing the same as the matched_percentage field of account.move, except in case of multi-currencies
        where we recompute the matched percentage based on the amount_currency fields.
        Note that this function is used only by the tax cash basis module since we want to consider the matched_percentage only
        based on the company currency amounts in reports.
        """
        matched_percentage_per_move = {}
        for line in self:
            if not matched_percentage_per_move.get(line.move_id.id, False):
                lines_to_consider = line.move_id.line_ids.filtered(lambda x: x.account_id.internal_type in ('receivable', 'payable'))
                total_amount_currency = 0.0
                total_reconciled_currency = 0.0
                all_same_currency = False
                #if all receivable/payable aml and their payments have the same currency, we can safely consider
                #the amount_currency fields to avoid including the exchange rate difference in the matched_percentage
                if lines_to_consider and all([x.currency_id.id == lines_to_consider[0].currency_id.id for x in lines_to_consider]):
                    all_same_currency = lines_to_consider[0].currency_id.id
                    for line in lines_to_consider:
                        if all_same_currency:
                            total_amount_currency += abs(line.amount_currency)
                            for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                                if partial_line.currency_id and partial_line.currency_id.id == all_same_currency:
                                    total_reconciled_currency += partial_line.amount_currency
                                else:
                                    all_same_currency = False
                                    break
                if not all_same_currency:
                    #we cannot rely on amount_currency fields as it is not present on all partial reconciliation
                    matched_percentage_per_move[line.move_id.id] = line.move_id.matched_percentage
                else:
                    #we can rely on amount_currency fields, which allow us to post a tax cash basis move at the initial rate
                    #to avoid currency rate difference issues.
                    if total_amount_currency == 0.0:
                        matched_percentage_per_move[line.move_id.id] = 1.0
                    else:
                        matched_percentage_per_move[line.move_id.id] = total_reconciled_currency / total_amount_currency
        return matched_percentage_per_move
