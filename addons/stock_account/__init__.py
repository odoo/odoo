# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard


def _configure_product_categories(env):
    # the properties were not set because the fields didn't exist yet on the product categories
    for company in env['res.company'].search([('chart_template', '!=', False)]):
        journal = env['account.journal'].search([
            ('code', '=', 'STJ'),
            ('company_id', '=', company.id),
            ('type', '=', 'general')], limit=1)
        if journal:
            env['ir.model.data']._update_xmlids([{
                'xml_id': f"account.{company.id}_inventory_valuation",
                'record': journal,
                'noupdate': True,
            }])
        ChartTemplate = env['account.chart.template'].with_company(company)
        template_code = company.chart_template
        template_data = ChartTemplate._get_chart_template_data(template_code)['template_data']
        ChartTemplate._post_load_data(template_code, company, {
            fname: value
            for fname, value in template_data.items()
            if fname in [
                'property_stock_account_input_categ_id',
                'property_stock_account_output_categ_id',
                'property_stock_valuation_account_id',
            ]
        })
