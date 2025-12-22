from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'vn')], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        data = {
            'account.tax.group': ChartTemplate._get_account_tax_group(company.chart_template),
            'account.tax': ChartTemplate._get_account_tax(company.chart_template)
        }
        ChartTemplate._pre_reload_data(company, {}, data, force_create=False)
        ChartTemplate._load_data(data)
