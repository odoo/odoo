# Part of Odoo. See LICENSE file for full copyright and licensing details.

def post_init_hook(env):
    for company in env['res.company'].search([('chart_template', '=', 'pe')]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        tax_group_data = ChartTemplate._get_pe_edi_account_tax_group()
        ChartTemplate._load_data({'account.tax.group': tax_group_data})
