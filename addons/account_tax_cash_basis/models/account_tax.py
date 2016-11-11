# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    use_cash_basis = fields.Boolean(
        'Use Cash Basis',
        help="Select this if the tax should use cash basis,"
        "which will create an entry for this tax on a given account during reconciliation")
    cash_basis_account = fields.Many2one(
        'account.account',
        string='Tax Received Account',
        domain=[('deprecated', '=', False)],
        help='Account use when creating entry for tax cash basis')
