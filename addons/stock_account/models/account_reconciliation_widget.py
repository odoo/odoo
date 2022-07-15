# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    @api.model
    def _domain_move_lines_for_reconciliation(self, st_line, aml_accounts, partner_id, excluded_ids=None, search_str=False, mode='rp'):
        domain = super()._domain_move_lines_for_reconciliation(
            st_line, aml_accounts, partner_id, excluded_ids=excluded_ids, search_str=search_str, mode=mode
        )
        account_stock_properties_names = [
            "property_stock_account_input",
            "property_stock_account_output",
            "property_stock_account_input_categ_id",
            "property_stock_account_output_categ_id",
        ]
        properties = self.env['ir.property'].sudo().search([
            ('name', 'in', account_stock_properties_names),
            ('company_id', '=', self.env.company.id),
            ('value_reference', '!=', False),
        ])

        if properties:
            accounts = properties.mapped(lambda p: p.get_by_record())
            domain.append(('account_id', 'not in', tuple(accounts.ids)))
        return domain
