# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError

class AccountTaxCashBasis(models.Model):
    _inherit = 'account.tax'

    use_cash_basis = fields.Boolean('Use Cash Basis', help='Select this if the tax should use cash basis, which will \
        create an entry for this tax on a given account during reconciliation')
    cash_basis_account = fields.Many2one('account.account', string='Tax Received Account', domain=[('deprecated', '=', False)], help='Account use when \
        creating entry for tax cash basis')


class AccountMoveCashBasis(models.Model):
    _inherit = 'account.move'

    tax_cash_basis_rec_id = fields.Many2one('account.partial.reconcile', string='Tax Cash Basis Entry of', help="Technical field used to keep track of the tax cash basis reconciliation. This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    tax_cash_basis_journal_id = fields.Many2one('account.journal',
        related='company_id.tax_cash_basis_journal_id',
        string="Tax Cash Basis Journal",)


class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_cash_basis_journal_id = fields.Many2one('account.journal', string="Tax Cash Basis Journal")


class AccountPartialReconcileCashBasis(models.Model):
    _inherit = 'account.partial.reconcile'

    def _check_tax_exigible(self, line):
        """ Function overwritten in account_tax_exigible to make sure we consider only the lines having tax_exigible set to False """
        return False

    def _get_tax_cash_basis_lines(self, value_before_reconciliation):
        # Search in account_move if we have any taxes account move lines
        tax_group = {}
        total_by_cash_basis_account = {}
        line_to_create = []
        move_date = self.debit_move_id.date
        for move in (self.debit_move_id.move_id, self.credit_move_id.move_id):
            if move_date < move.date:
                move_date = move.date
            for line in move.line_ids:
                #TOCHECK: normal and cash basis taxes shoudn't be mixed together (on the same invoice line for example) as it will
                #create reporting issues. Not sure of the behavior to implement in that case, though.
                # amount to write is the current cash_basis amount minus the one before the reconciliation
                currency_id = line.currency_id or line.company_id.currency_id
                matched_percentage = value_before_reconciliation[move.id]
                amount = currency_id.round((line.credit_cash_basis - line.debit_cash_basis) - (line.credit - line.debit) * matched_percentage)
                if not self._check_tax_exigible(line):
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
                    if any([tax.use_cash_basis for tax in line.tax_ids]):
                        for tax in line.tax_ids:
                            line_to_create.append((0, 0, {
                                'name': '/',
                                'debit': currency_id.round(line.debit_cash_basis - line.debit * matched_percentage),
                                'credit': currency_id.round(line.credit_cash_basis - line.credit * matched_percentage),
                                'account_id': line.account_id.id,
                                'tax_ids': [(6, 0, [tax.id])],
                                }))
                            line_to_create.append((0, 0, {
                                'name': '/',
                                'credit': currency_id.round(line.debit_cash_basis - line.debit * matched_percentage),
                                'debit': currency_id.round(line.credit_cash_basis - line.credit * matched_percentage),
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
                }))
        return line_to_create, move_date

    def create_tax_cash_basis_entry(self, value_before_reconciliation):
        line_to_create, move_date = self._get_tax_cash_basis_lines(value_before_reconciliation)
        if len(line_to_create) > 0:
            # Check if company_journal for cash basis is set if not, raise exception
            if not self.company_id.tax_cash_basis_journal_id:
                raise UserError(_('There is no tax cash basis journal defined ' \
                                    'for this company: "%s" \nConfigure it in Accounting/Configuration/Settings') % \
                                      (self.company_id.name))
            move_vals = {
                'journal_id': self.company_id.tax_cash_basis_journal_id.id,
                'line_ids': line_to_create,
                'tax_cash_basis_rec_id': self.id
            }
            # The move date should be the maximum date between payment and invoice (in case
            # of payment in advance). However, we should make sure the move date is not
            # recorded after the period lock date as the tax statement for this period is
            # probably already sent to the estate.
            if move_date > self.company_id.period_lock_date:
                move_vals['date'] = move_date
            move = self.env['account.move'].with_context(dont_create_taxes=True).create(move_vals)
            # post move
            move.post()

    @api.model
    def create(self, vals):
        aml = []
        if vals.get('debit_move_id', False):
            aml.append(vals['debit_move_id'])
        if vals.get('credit_move_id', False):
            aml.append(vals['credit_move_id'])
        #Get value of matched percentage from both move before reconciliating
        lines = self.env['account.move.line'].browse(aml)
        value_before_reconciliation = {}
        for line in lines:
            if not value_before_reconciliation.get(line.move_id.id, False):
                value_before_reconciliation[line.move_id.id] = line.move_id.matched_percentage
        #Reconcile
        res = super(AccountPartialReconcileCashBasis, self).create(vals)
        #eventually create a tax cash basis entry
        res.create_tax_cash_basis_entry(value_before_reconciliation)
        return res

    @api.multi
    def unlink(self):
        move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', self._ids)])
        move.reverse_moves()
        super(AccountPartialReconcileCashBasis, self).unlink()
