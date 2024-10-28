from odoo import api


def migrate(cr, version):
    env = api.Environment(cr, api.SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', 'like', r'es\_%')]):
        env['account.chart.template'].try_loading(company.chart_template, company)
