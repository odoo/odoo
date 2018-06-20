# -*- coding: utf-8 -*-

from openerp import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    cash_basis_base_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)],
        string='Base Tax Received Account',
        help='Account that will be set on lines created in cash basis journal entry and used to keep track of the tax base amount.')
