# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """ Update taxes for existing companies, in order to apply the new tags to them. """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'my')], order="parent_path"):
        env['account.chart.template'].try_loading('my', company)
