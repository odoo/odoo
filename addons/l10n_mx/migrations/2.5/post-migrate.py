from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Runs in post- so the account exists before sale's upgrade sets the accrual accounts from the template.
    for company in env['res.company'].search([('chart_template', '=', 'mx'), ('parent_id', '=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        accounts = ChartTemplate._get_account_account('mx')
        data = {'account.account': {'cuenta115_05_02': accounts['cuenta115_05_02']}}
        ChartTemplate._pre_reload_data(company, {}, data)
        ChartTemplate._load_data(data)
        ChartTemplate._load_translations(companies=company, template_data=data)
