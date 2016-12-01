# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountPartialReconcileCashBasis(models.Model):
    _inherit = 'account.partial.reconcile'

    def create_tax_cash_basis_entry(self, percentage_before_rec):
        self.ensure_one()
        move_date = self.debit_move_id.date
        newly_created_move = self.env['account.move']
        for move in (self.debit_move_id.move_id, self.credit_move_id.move_id):
            #move_date is the max of the 2 reconciled items
            if move_date < move.date:
                move_date = move.date
            for line in move.line_ids:
                #TOCHECK: normal and cash basis taxes shoudn't be mixed together (on the same invoice line for example) as it will
                # create reporting issues. Not sure of the behavior to implement in that case, though.
                if not line.tax_exigible:
                    percentage_before = percentage_before_rec[move.id]
                    percentage_after = line._get_matched_percentage()[move.id]
                    #amount is the current cash_basis amount minus the one before the reconciliation
                    amount = line.balance * percentage_after - line.balance * percentage_before
                    rounded_amt = line.company_id.currency_id.round(amount)
                    if line.tax_line_id and line.tax_line_id.use_cash_basis:
                        if not newly_created_move:
                            newly_created_move = self._create_tax_basis_move()
                        #create cash basis entry for the tax line
                        to_clear_aml = self.env['account.move.line'].with_context(check_move_validity=False).create({
                            'name': line.move_id.name,
                            'debit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                            'credit': rounded_amt if rounded_amt > 0 else 0.0,
                            'account_id': line.account_id.id,
                            'tax_exigible': True,
                            'amount_currency': self.amount_currency and line.currency_id.round(-line.amount_currency * amount / line.balance) or 0.0,
                            'currency_id': line.currency_id.id,
                            'move_id': newly_created_move.id,
                            })
                        # Group by cash basis account and tax
                        self.env['account.move.line'].with_context(check_move_validity=False).create({
                            'name': line.name,
                            'debit': rounded_amt if rounded_amt > 0 else 0.0,
                            'credit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                            'account_id': line.tax_line_id.cash_basis_account.id,
                            'tax_line_id': line.tax_line_id.id,
                            'tax_exigible': True,
                            'amount_currency': self.amount_currency and line.currency_id.round(line.amount_currency * amount / line.balance) or 0.0,
                            'currency_id': line.currency_id.id,
                            'move_id': newly_created_move.id,
                        })
                        if line.account_id.reconcile:
                            #setting the account to allow reconciliation will help to fix rounding errors
                            to_clear_aml |= line
                            to_clear_aml.reconcile()

                    if any([tax.use_cash_basis for tax in line.tax_ids]):
                        #create cash basis entry for the base
                        for tax in line.tax_ids:
                            self.env['account.move.line'].with_context(check_move_validity=False).create({
                                'name': line.name,
                                'debit': rounded_amt > 0 and rounded_amt or 0.0,
                                'credit': rounded_amt < 0 and abs(rounded_amt) or 0.0,
                                'account_id': line.account_id.id,
                                'tax_exigible': True,
                                'tax_ids': [(6, 0, [tax.id])],
                                'move_id': newly_created_move.id,
                                'currency_id': line.currency_id.id,
                                'amount_currency': self.amount_currency and line.currency_id.round(line.amount_currency * amount / line.balance) or 0.0,
                            })
                            self.env['account.move.line'].with_context(check_move_validity=False).create({
                                'name': line.name,
                                'credit': rounded_amt > 0 and rounded_amt or 0.0,
                                'debit': rounded_amt < 0 and abs(rounded_amt) or 0.0,
                                'account_id': line.account_id.id,
                                'tax_exigible': True,
                                'move_id': newly_created_move.id,
                                'currency_id': line.currency_id.id,
                                'amount_currency': self.amount_currency and line.currency_id.round(-line.amount_currency * amount / line.balance) or 0.0,
                            })
            if newly_created_move:
                if move_date > self.company_id.period_lock_date and newly_created_move.date != move_date:
                    # The move date should be the maximum date between payment and invoice (in case
                    # of payment in advance). However, we should make sure the move date is not
                    # recorded before the period lock date as the tax statement for this period is
                    # probably already sent to the estate.
                    newly_created_move.write({'date': move_date})
                # post move
                newly_created_move.post()
            # Only entries with cash flow must be created
            if not self.company_id.currency_id.is_zero(v):

    def _create_tax_basis_move(self):
        # Check if company_journal for cash basis is set if not, raise exception
        if not self.company_id.tax_cash_basis_journal_id:
            raise UserError(_('There is no tax cash basis journal defined '
                              'for this company: "%s" \nConfigure it in Accounting/Configuration/Settings') %
                            (self.company_id.name))
        move_vals = {
            'journal_id': self.company_id.tax_cash_basis_journal_id.id,
            'tax_cash_basis_rec_id': self.id,
        }
        return self.env['account.move'].create(move_vals)

    @api.model
    def create(self, vals):
        aml = []
        if vals.get('debit_move_id', False):
            aml.append(vals['debit_move_id'])
        if vals.get('credit_move_id', False):
            aml.append(vals['credit_move_id'])
        # Get value of matched percentage from both move before reconciliating
        lines = self.env['account.move.line'].browse(aml)
        percentage_before_rec = lines._get_matched_percentage()
        # Reconcile
        res = super(AccountPartialReconcileCashBasis, self).create(vals)
        # if the reconciliation is a matching on a receivable or payable account, eventually create a tax cash basis entry
        if lines[0].account_id.internal_type in ('receivable', 'payable'):
            res.create_tax_cash_basis_entry(percentage_before_rec)
        return res

    @api.multi
    def unlink(self):
        move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', self._ids)])
        move.reverse_moves()
        super(AccountPartialReconcileCashBasis, self).unlink()
