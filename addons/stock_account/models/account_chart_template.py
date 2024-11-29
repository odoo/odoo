# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        company = company or self.env.company
        fields_name = self.env['product.category']._get_stock_account_property_field_names()
        ProductCategory = self.env['product.category'].with_company(company.id)
        for fname in fields_name:
            fallback = ProductCategory._fields[fname].get_company_dependent_fallback(ProductCategory).id
            if ProductCategory.search_count([(fname, '!=', fallback)], limit=1):
                continue
            value = template_data.get(fname)
            if value:
                self.env['ir.default'].set('product.category', fname, self.ref(value).id, company_id=company.id)

    @template(model='account.journal')
    def _get_stock_account_journal(self, template_code):
        return {
            'inventory_valuation': {
                'name': _('Inventory Valuation'),
                'code': 'STJ',
                'type': 'general',
                'sequence': 10,
                'show_on_dashboard': False,
            },
        }

    @template()
    def _get_stock_template_data(self, template_code):
        return {
            'property_stock_journal': 'inventory_valuation',
        }
