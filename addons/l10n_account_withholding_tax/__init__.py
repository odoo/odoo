# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from . import models
from . import wizards


def _l10n_account_wth_post_init(env):
    """ Set up a demo tax and add it to service products to help with testing/demoing. """
    if env.ref('base.module_l10n_account_withholding_tax').demo:
        companies = env['res.company'].search([('chart_template', '!=', False)], order="parent_path")
        for template_code, companies in companies.grouped('chart_template').items():
            for company in companies:
                ChartTemplate = env['account.chart.template'].with_company(company)
                chart_template_data = ChartTemplate._get_chart_template_data(template_code)
                _make_demo_tax(ChartTemplate, chart_template_data)


def _make_demo_tax(chart_template, chart_template_data):
    # We take the accounts from the first purchase tax we find in the template data.
    tax_data = chart_template_data.get('account.tax')
    purchase_taxes = [tax for tax in tax_data if tax_data[tax]['type_tax_use'] == 'purchase' and tax_data[tax].get('repartition_line_ids')]
    if not purchase_taxes:
        return

    tax_repartition_lines = [line[2] for line in tax_data[purchase_taxes[0]]['repartition_line_ids'] if line[2]['repartition_type'] == 'tax']
    if not tax_repartition_lines or 'account_id' not in tax_repartition_lines[0] or not tax_repartition_lines[0]['account_id']:
        return

    account_id = tax_repartition_lines[0]['account_id']
    account = chart_template.ref(account_id)

    # We will also add a basic default sequence to ease demo; this avoid needing to give a random sequence when registering a tax.
    wh_tax = chart_template.env['account.tax'].create({
        'name': '2% WTH',
        'type_tax_use': 'purchase',
        'is_withholding_tax_on_payment': True,
        'amount_type': 'percent',
        'amount': -2,
        'company_id': chart_template.env.company.id,
        'price_include_override': 'tax_excluded',
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
        'withholding_sequence_id': chart_template.env['ir.sequence'].create({
            'name': 'Purchase wth sequence',
            'padding': 1,
            'number_increment': 1,
            'implementation': 'standard',
            'company_id': chart_template.env.company.id,
        }).id,
    })
    # Add the tax on both demo services
    (chart_template.ref('product.product_product_1') | chart_template.ref('product.product_product_2')).supplier_taxes_id += wh_tax
