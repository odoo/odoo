# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards

from odoo import Command


def _l10n_account_withholding_post_init(env):
    """ For existing companies with a chart template that is not from argentina """
    excluded_templates = ['ar_ri', 'ar_ex', 'ar_base', False]
    companies = env['res.company'].search([('chart_template', 'not in', excluded_templates)], order="parent_path")
    for template_code, companies in companies.grouped('chart_template').items():
        chart_template_data = env['account.chart.template']._get_chart_template_data(template_code)
        template_data = chart_template_data.pop('template_data')
        for company in companies:
            if company.parent_id or company.l10n_account_withholding_tax_base_account_id:
                continue

            code_digits = int(template_data.get('code_digits', 6))
            company.l10n_account_withholding_tax_base_account_id = env['account.account']._load_records([{
                'xml_id': f"account.{company.id}_l10n_account_withholding_tax_base_account_id",
                'values': {
                    'name': env._("WHT BASE AMOUNT"),
                    'prefix': '998',
                    'code_digits': code_digits,
                    'account_type': 'asset_current',
                    'reconcile': True,
                },
                'noupdate': True,
            }])

            # We also want to set up a demo tax and put it on the service demo products; to ease testing/...
            if env.ref('base.module_l10n_account_withholding').demo:
                _make_demo_tax(env, chart_template_data, company)


def _make_demo_tax(env, chart_template_data, company):
    # We take the accounts from the first purchase tax we find in the template data.
    tax_data = chart_template_data.get('account.tax')
    purchase_taxes = [tax for tax in tax_data if tax_data[tax]['type_tax_use'] == 'purchase']
    if not purchase_taxes:
        return

    tax_repartition_lines = [line[2] for line in tax_data[purchase_taxes[0]]['repartition_line_ids'] if line[2]['repartition_type'] == 'tax']
    if not tax_repartition_lines or 'account_id' not in tax_repartition_lines[0] or not tax_repartition_lines[0]['account_id']:
        return

    account_id = tax_repartition_lines[0]['account_id']
    account = env.ref(f'account.{company.id}_{account_id}')

    # We will also add a basic default sequence to ease demo; this avoid needing to give a random sequence when registering a tax.
    wh_tax = env['account.tax'].create({
        'name': '2% WTH',
        'type_tax_use': 'purchases_wth',
        'amount_type': 'percent',
        'amount': 2,
        'company_id': company.id,
        'invoice_repartition_line_ids': [
            Command.create({
                'repartition_type': 'base',
            }),
            Command.create({
                'repartition_type': 'tax',
                'account_id': account.id,
            }),
        ],
        'refund_repartition_line_ids': [
            Command.create({
                'repartition_type': 'base',
            }),
            Command.create({
                'repartition_type': 'tax',
                'account_id': account.id,
            }),
        ],
        'l10n_account_withholding_sequence_id': env['ir.sequence'].create({
            'name': 'Purchase wth sequence',
            'padding': 1,
            'number_increment': 1,
            'implementation': 'standard',
            'company_id': company.id,
        }).id,
    })
    # Add the tax on both demo services
    (env.ref('product.product_product_1') | env.ref('product.product_product_2')).supplier_taxes_id += wh_tax
