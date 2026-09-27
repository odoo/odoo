from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'pl'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)

        template_data = Template._get_chart_template_data('pl').get('template_data', {})
        data = {'account.account': Template._get_account_account('pl')}

        Template._pre_reload_data(company, template_data, data, True)
        Template._load_data(data)
