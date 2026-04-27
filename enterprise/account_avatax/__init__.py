# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import wizard


def _post_init_hook(env):
    """ Create the Avatax fiscal position in all US companies at the same time """
    if companies := env['res.company'].search([('chart_template', '=', 'generic_coa')], order="parent_path"):
        avatax_fiscal_position = env['account.chart.template']._get_us_avatax_fiscal_position()
        for company in companies:
            Template = env['account.chart.template'].with_company(company)
            Template._load_data({'account.fiscal.position': avatax_fiscal_position})
