# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, api, _
from openerp.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    tax_exigible = fields.Boolean(string='Appears in VAT report', default=True,
        help="Technical field used to mark a tax line as exigible in the vat report or not (only exigible journal items are displayed). By default all new journal items are directly exigible, but with the module account_tax_cash_basis, some will become exigible only when the payment is recorded.")

    @api.model
    def create(self, vals, apply_taxes=True):
        taxes = False
        if vals.get('tax_line_id'):
            taxes = [{'use_cash_basis': self.env['account.tax'].browse(vals['tax_line_id']).use_cash_basis}]
        if vals.get('tax_ids'):
            taxes = self.env['account.move.line'].resolve_2many_commands('tax_ids', vals['tax_ids'])
        if taxes and any([tax['use_cash_basis'] for tax in taxes]) and not vals.get('tax_exigible'):
            vals['tax_exigible'] = False
        return super(AccountMoveLine, self).create(vals, apply_taxes=apply_taxes)

class AccountPartialReconcileCashBasis(models.Model):
    _inherit = 'account.partial.reconcile'

    def create_tax_cash_basis_entry(self, value_before_reconciliation):
        # Search in account_move if we have any taxes account move lines
        tax_group = {}
        total_by_cash_basis_account = {}
        line_to_create = []
        for move in (self.debit_move_id.move_id, self.credit_move_id.move_id):
            for line in move.line_ids:
                #TOCHECK: normal and cash basis taxes shoudn't be mixed together (on the same invoice line for example) as it will
                #create reporting issues. Not sure of the behavior to implement in that case, though.
                if not line.tax_exigible:
                    # amount to write is the current cash_basis amount minus the one before the reconciliation
                    matched_percentage = value_before_reconciliation[move.id]
                    amount = (line.credit_cash_basis - line.debit_cash_basis) - (line.credit - line.debit) * matched_percentage
                    if line.tax_line_id and line.tax_line_id.use_cash_basis:
                        # group by line account
                        acc = line.account_id.id
                        if tax_group.get(acc, False):
                            tax_group[acc] += amount
                        else:
                            tax_group[acc] = amount
                        # Group by cash basis account and tax
                        acc = line.tax_line_id.cash_basis_account.id
                        key = (acc, line.tax_line_id.id)
                        if key in total_by_cash_basis_account:
                            total_by_cash_basis_account[key] += amount
                        else:
                            total_by_cash_basis_account[key] = amount
                    for tax in line.tax_ids:
                        if tax.use_cash_basis:
                            line_to_create.append((0, 0, {
                                'name': '/',
                                'debit': line.debit_cash_basis - line.debit * matched_percentage,
                                'credit': line.credit_cash_basis - line.credit * matched_percentage,
                                'account_id': line.account_id.id,
                                'tax_ids': [(6, 0, [tax.id])],
                                'tax_exigible': True,
                                }))
                            line_to_create.append((0, 0, {
                                'name': '/',
                                'credit': line.debit_cash_basis - line.debit * matched_percentage,
                                'debit': line.credit_cash_basis - line.credit * matched_percentage,
                                'account_id': line.account_id.id,
                                }))

        for k, v in tax_group.items():
            line_to_create.append((0, 0, {
                'name': '/',
                'debit': v if v > 0 else 0.0,
                'credit': abs(v) if v < 0 else 0.0,
                'account_id': k,
                }))

        # Create counterpart vals
        for key, v in total_by_cash_basis_account.items():
            k, tax_id = key
            line_to_create.append((0, 0, {
                'name': '/',
                'debit': abs(v) if v < 0 else 0.0,
                'credit': v if v > 0 else 0.0,
                'account_id': k,
                'tax_line_id': tax_id,
                'tax_exigible': True,
                }))

        # Create move
        if len(line_to_create) > 0:
            # Check if company_journal for cash basis is set if not, raise exception
            if not self.company_id.tax_cash_basis_journal_id:
                raise UserError(_('There is no tax cash basis journal defined ' \
                                    'for this company: "%s" \nConfigure it in Accounting/Configuration/Settings') % \
                                      (self.company_id.name))
            move = self.env['account.move'].with_context(dont_create_taxes=True).create({
                'journal_id': self.company_id.tax_cash_basis_journal_id.id,
                'line_ids': line_to_create,
                'tax_cash_basis_rec_id': self.id})
            # post move
            move.post()
