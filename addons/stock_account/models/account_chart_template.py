# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

<<<<<<< 17.0
    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        company = company or self.env.company
        fields_name = self.env['product.category']._get_stock_account_property_field_names()
        account_fields = self.env['ir.model.fields'].search([('model', '=', 'product.category'), ('name', 'in', fields_name)])
        existing_props = self.env['ir.property'].sudo().search([
            ('fields_id', 'in', account_fields.ids),
            ('company_id', '=', company.id),
            ('res_id', '!=', False),
        ])
        for fname in fields_name:
            if fname in existing_props.mapped('fields_id.name'):
                continue
            value = template_data.get(fname)
            if value:
                self.env['ir.property']._set_default(fname, 'product.category', self.ref(value).id, company=company)
||||||| 315279c7aaefb6e0194fdd15e39ef3f19adf451c
    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        journal_to_add = [{'name': _('Inventory Valuation'), 'type': 'general', 'code': 'STJ', 'favorite': False, 'sequence': 8}]
        return super(AccountChartTemplate, self).generate_journals(acc_template_ref=acc_template_ref, company=company, journals_dict=journal_to_add)
=======
    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        journal_to_add = (journals_dict or []) + [{'name': _('Inventory Valuation'), 'type': 'general', 'code': 'STJ', 'favorite': False, 'sequence': 8}]
        return super(AccountChartTemplate, self).generate_journals(acc_template_ref=acc_template_ref, company=company, journals_dict=journal_to_add)
>>>>>>> 74b590d86fc051ed697cdb312a7c19aaca72183a

    @template(model='account.journal')
    def _get_stock_account_journal(self, template_code):
        return {
            'inventory_valuation': {
                'name': _('Inventory Valuation'),
                'code': 'STJ',
                'type': 'general',
                'sequence': 8,
                'show_on_dashboard': False,
            },
        }

    @template()
    def _get_stock_template_data(self, template_code):
        return {
            'property_stock_journal': 'inventory_valuation',
        }
