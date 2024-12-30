# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models

def post_init_hook(env):
    for company in env['res.company'].search([('chart_template', '=like', 'be%')], order="parent_path"):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': Template._get_be_pos_restaurant_account_tax(),
        })
