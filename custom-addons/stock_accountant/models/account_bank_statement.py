# -*- coding: utf-8 -*-
from odoo import models
from odoo.osv import expression


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_default_amls_matching_domain(self):
        # EXTENDS account
        domain = super()._get_default_amls_matching_domain()

        blacklisted_stock_account_ids = set()
        account_stock_properties_names = [
            'property_stock_account_input',
            'property_stock_account_output',
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
        ]

        properties = self.env['ir.property'].sudo().search([
            ('name', 'in', account_stock_properties_names),
            ('company_id', '=', self.env.company.id),
            ('value_reference', '!=', False),
        ])
        if properties:
            accounts = properties.mapped(lambda p: p.get_by_record())
            blacklisted_stock_account_ids.update(accounts.ids)

        if blacklisted_stock_account_ids:
            return expression.AND([domain, [('account_id', 'not in', tuple(blacklisted_stock_account_ids))]])
        else:
            return domain
