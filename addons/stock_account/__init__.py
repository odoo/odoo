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
    products = env['product.product'].with_context(prefetch_fields=False).search([('type', '=', 'consu')])
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
    env['product.value'].with_context(prefetch_fields=False).create(product_vals_list)


def _configure_journals(env):
    for company in env['res.company'].search([('chart_template', '!=', False)], order="parent_path"):
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


def _configure_stock_account_company_data(env):
<<<<<<< 549ce2754ff640864da8c07ef345861c4f39ec5c
    env['account.chart.template']._load_pre_defined_data({
        'res.company': {
            'account_stock_valuation_id',
            'account_production_wip_account_id',
            'account_production_wip_overhead_account_id',
        },
        'account.account': {
            'account_stock_expense_id',
            'account_stock_variation_id',
        },
    })
||||||| 956643b90753fbbe285bbe1797577964753dee99
    for company in env['res.company'].search([('chart_template', '!=', False)], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        template_code = company.chart_template
        res_company_data = ChartTemplate._get_stock_account_res_company(template_code)
        account_account_data = ChartTemplate._get_stock_account_account(template_code)
        ChartTemplate._load_data({
            'res.company': res_company_data,
            'account.account': account_account_data,
        })
=======
    for company in env['res.company'].search([('chart_template', '!=', False)], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        template_code = company.chart_template
        res_company_data = ChartTemplate._get_stock_account_res_company(template_code)
        account_account_data = ChartTemplate._get_stock_account_account(template_code)
        account_templates = ChartTemplate._get_chart_template_model_data(template_code, 'account.account')
        for xmlid, vals in account_account_data.items():
            if not ChartTemplate.ref(xmlid, raise_if_not_found=False):
                vals.update(account_templates.get(xmlid, {}))
        ChartTemplate._load_data({
            'res.company': res_company_data,
            'account.account': account_account_data,
        })
>>>>>>> 21b0cd4dc696f96c01f2d3adf8ee6fa66a51d38b
