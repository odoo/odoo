from . import models


def post_init_hook(env):
    for company in env['res.company'].search([('chart_template', '=', 'in')]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'account.account': ChartTemplate._get_in_tcs_account_account(),
            'account.tax.group': ChartTemplate._get_in_tcs_account_tax_group(),
            'account.tax': ChartTemplate._get_in_tcs_account_tax(),
        })
