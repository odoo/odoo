# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields

from . import models
from . import report
from . import wizard


def _post_init_hook(env):
    _configure_journals(env)
    _create_product_value(env)
    _configure_stock_account_company_data(env)


def _create_product_value(env):
    product_vals_list = []
    products = env['product.product'].search([('type', '=', 'consu')])
    for company in env['res.company'].search([]):
        products = products.with_company(company)
        product_vals_list += [
            {
                'product_id': product.id,
                'value': product.standard_price,
                'date': fields.Date.today(),
                'company_id': company.id,
                'description': 'Initial cost',
            }
            for product in products if not product.company_id or product.company_id == company
        ]
    env['product.value'].create(product_vals_list)


def _configure_journals(env):
    # if we already have a coa installed, create journal and set property field
    for company in env['res.company'].search([('chart_template', '!=', False)], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        template_code = company.chart_template
        full_data = ChartTemplate._get_chart_template_data(template_code)
        data = {
            'template_data': {
                fname: value
                for fname, value in full_data['template_data'].items()
                if fname in [
                    'stock_journal',
                    'stock_valuation_account_id',
                ]
            }
        }
        data['res.company'] = {company.id: {
            'account_stock_journal_id': full_data['res.company'][company.id].get('account_stock_journal_id'),
            'account_stock_valuation_id': full_data['res.company'][company.id].get('account_stock_valuation_id'),
        }}

        template_data = data.pop('template_data')
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
        else:
            data['account.journal'] = ChartTemplate._get_stock_account_journal(template_code)

        ChartTemplate._load_data(data)
        ChartTemplate._post_load_data(template_code, company, template_data)


def _configure_stock_account_company_data(env):
    for company in env['res.company'].search([('chart_template', '!=', False)], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        template_code = company.chart_template
        res_company_data = ChartTemplate._get_stock_account_res_company(template_code)
        account_account_data = ChartTemplate._get_stock_account_account(template_code)
        ChartTemplate._load_data({
            'res.company': res_company_data,
            'account.account': account_account_data,
        })
