# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, api


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

    def _check_tax_exigible(self, line):
        return line.tax_exigible

    def _get_tax_cash_basis_lines(self, value_before_reconciliation):
        lines, move_date = super(AccountPartialReconcileCashBasis, self)._get_tax_cash_basis_lines(value_before_reconciliation)
        for i in range(len(lines)):
            vals = lines[i][2]
            vals['tax_exigible'] = True
            lines[i] = (0, 0, vals)
        return lines, move_date
