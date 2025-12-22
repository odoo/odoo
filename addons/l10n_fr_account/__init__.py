# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr
from . import models
from . import wizard

from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes


def _l10n_fr_post_init_hook(env):
    _preserve_tag_on_taxes(env)
    _setup_inalterability(env)

def _preserve_tag_on_taxes(env):
    preserve_existing_tags_on_taxes(env, 'l10n_fr_account')

def _setup_inalterability(env):
    # enable ping for this module
    env['publisher_warranty.contract'].update_notification(cron_mode=True)

    fr_companies = env['res.company'].search([('partner_id.country_id.code', 'in', env['res.company']._get_france_country_codes())])
    if fr_companies:
        fr_companies._create_secure_sequence(['l10n_fr_closing_sequence_id'])
