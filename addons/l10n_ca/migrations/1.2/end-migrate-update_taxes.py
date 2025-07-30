# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    all_fiscal_positions = [
        'fiscal_position_template_ab',
        'fiscal_position_template_bc',
        'fiscal_position_template_mb',
        'fiscal_position_template_nb',
        'fiscal_position_template_nl',
        'fiscal_position_template_ns',
        'fiscal_position_template_nt',
        'fiscal_position_template_nu',
        'fiscal_position_template_on',
        'fiscal_position_template_pe',
        'fiscal_position_template_qc',
        'fiscal_position_template_sk',
        'fiscal_position_template_yt',
        'fiscal_position_template_intl',
    ]
    for company in env['res.company'].search([('chart_template', '=', 'ca_2023')], order="parent_path"):
        for fiscal_position_ref in all_fiscal_positions:
            fiscal_position = env['account.chart.template'].with_company(company).ref(fiscal_position_ref, raise_if_not_found=False)
            if fiscal_position:
                fiscal_position.tax_ids = False
        env['account.chart.template'].try_loading('ca_2023', company)
