# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID


def load_translations(env):
    env.ref('l10n_ch.l10nch_chart_template').process_coa_translations()


def init_settings(env):
    '''If the company is localized in Switzerland, activate the cash rounding by default.
    '''
    # The cash rounding is activated by default only if the company is localized in Switzerland.
    ch_country = env.ref('base.ch')
    for company in env['res.company'].search([('partner_id.country_id', '=', ch_country.id)]):
        res_config_id = env['res.config.settings'].create({
            'company_id': company.id,
            'group_cash_rounding': True
        })
        # We need to call execute, otherwise the "implied_group" in fields are not processed.
        res_config_id.execute()


def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    load_translations(env)
    init_settings(env)
