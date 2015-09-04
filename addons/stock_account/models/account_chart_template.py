# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        journal_to_add = [{'name': _('Stock Journal'), 'type': 'general', 'code': 'STJ', 'favorite': False, 'sequence': 8}]
        super(AccountChartTemplate, self).generate_journals(acc_template_ref=acc_template_ref, company=company, journals_dict=journal_to_add)

    @api.multi
    def generate_properties(self, acc_template_ref, company, property_list=None):
        super(AccountChartTemplate, self).generate_properties(acc_template_ref=acc_template_ref, company=company)
        IrProperty = self.env['ir.property']
        value = self.env['account.journal'].search([('company_id', '=', company.id), ('code', '=', 'STJ'), ('type', '=', 'general')], limit=1)

        todo_list = [ # Property Stock Accounts
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ]
        if value:
            todo_list.append('property_stock_journal')

        for record in todo_list:
            if record == 'property_stock_journal':
                relation = 'account.journal'
                journal = value
            else:
                relation = 'account.account'
                account = getattr(self, record)
                journal = account and acc_template_ref.get(account.id)

            if journal:
                field = self.env['ir.model.fields'].search([('name', '=', record), ('model', '=', 'product.category'), ('relation', '=', relation)], limit=1)
                vals = {
                    'name': record,
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': journal,
                }
                properties = IrProperty.search([('name', '=', record), ('company_id', '=', company.id)])
                if properties:
                    #the property exist: modify it
                    properties.write(vals)
                else:
                    #create the property
                    IrProperty.create(vals)

        return True
