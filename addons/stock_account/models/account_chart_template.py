# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_journals(self, loaded_data):
        # OVERRIDE
        res = super()._prepare_journals(loaded_data)
        res['stock'] = [{
            'name': _('Inventory Valuation'),
            'type': 'general',
            'code': 'STJ',
            'sequence': 8,
            'company_id': self.env.company.id,
        }]
        return res

    def _create_properties(self, loaded_data):
        # OVERRIDE
        res = super()._create_properties(loaded_data)
        company = self.env.company
        accounts_mapping = loaded_data['account.account.template']['records']

        PropertyObj = self.env['ir.property']  # Property Stock Journal
        stock_journal = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('code', '=', 'STJ'),
            ('type', '=', 'general'),
        ], limit=1)
        if stock_journal:
            PropertyObj._set_default("property_stock_journal", "product.category", stock_journal, company)

        todo_list = [  # Property Stock Accounts
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ]
        for field_name in todo_list:
            if not self[field_name]:
                continue

            account = accounts_mapping[self[field_name]]
            PropertyObj._set_default(field_name, "product.category", account, company)

        return res
