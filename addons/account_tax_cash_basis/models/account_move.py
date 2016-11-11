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
