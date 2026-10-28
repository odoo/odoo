from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ChartTemplate = env['account.chart.template']

    companies = env['res.company'].search([('chart_template', '!=', False)], order="parent_path")
    for company in companies:
        if 'es_common' not in ChartTemplate._get_parent_template(company.chart_template):
            continue
        ChartTemplate.try_loading(company.chart_template, company)
