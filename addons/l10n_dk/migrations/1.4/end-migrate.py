from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'dk')], order='parent_path'):
        # Reload the accounts and tags that we updated.
        env['account.chart.template'].try_loading('dk', company)
