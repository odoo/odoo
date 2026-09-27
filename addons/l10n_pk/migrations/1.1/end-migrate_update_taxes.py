from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'pk')], order="parent_path"):
        env['account.chart.template'].try_loading('pk', company, force_create=False)
