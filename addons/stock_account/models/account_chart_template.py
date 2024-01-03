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
