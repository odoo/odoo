# -*- coding: utf-8 -*-
from odoo import models
from odoo.osv import expression


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_default_amls_matching_domain(self):
        # EXTENDS account
        domain = super()._get_default_amls_matching_domain()

        categories = self.env['product.category'].search([
            '|',
            ('property_stock_account_input_categ_id', '!=', False),
            ('property_stock_account_output_categ_id', '!=', False)
        ])
        accounts = (categories.mapped('property_stock_account_input_categ_id') +
                    categories.mapped('property_stock_account_output_categ_id'))
        if accounts:
            return expression.AND([domain, [('account_id', 'not in', tuple(set(accounts.ids)))]])
        return domain
