# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        company = company or self.env.company
        categ_values = {category.id: False for category in self.env['product.category'].search([])}
        for fname in self.env['product.category']._get_stock_account_property_field_names():
            self.env['ir.property'].with_company(company.id)._set_multi(fname, 'product.category', categ_values, True)
            value = template_data.get(fname)
            if value:
                self.env['ir.property']._set_default(fname, 'product.category', self.ref(value).id, company=company)

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
