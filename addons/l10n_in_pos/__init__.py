# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def pos_config_setting(env):
    for config in env['pos.config'].search([('company_id.account_fiscal_country_id.code', '=', 'IN')]):
        config.write({
            'is_closing_entry_by_product': True
        })


def post_init(env):
    pos_config_setting(env)
