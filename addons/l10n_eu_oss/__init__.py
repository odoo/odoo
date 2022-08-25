# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo import api, SUPERUSER_ID

def l10n_eu_oss_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.company']._map_all_eu_companies_taxes()

def l10n_eu_oss_uninstall(cr, registry):
    cr.execute("DELETE FROM ir_model_data WHERE module = 'l10n_eu_oss' and model in ('account.tax.group', 'account.account');")
