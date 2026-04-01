from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'ee')], order="parent_path"):
        env['account.chart.template'].try_loading('ee', company, force_create=False)
