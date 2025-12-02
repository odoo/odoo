# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'ca_2023')], order="parent_path"):
        fiscal_position = env['account.chart.template'].with_company(company).ref('fiscal_position_template_ns', raise_if_not_found=False)
        if fiscal_position:
            fiscal_position.tax_ids = False
        env['account.chart.template'].try_loading('ca_2023', company)
