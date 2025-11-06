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
