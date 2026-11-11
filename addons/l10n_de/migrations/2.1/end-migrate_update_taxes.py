# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for chart_template in ('de_skr03', 'de_skr04'):
        for company in env['res.company'].search([('chart_template', '=', chart_template)], order="parent_path"):
            env['account.chart.template'].try_loading(chart_template, company, force_create=False)
