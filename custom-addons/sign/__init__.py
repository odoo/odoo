# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard
from . import PYPDF2_MonkeyPatch

ITSME_AVAILABLE_COUNTRIES = ['BE', 'NL']


def _sign_post_init(env):
    # check if any company is within itsme available countries
    country_codes = env['res.company'].search([]).mapped('country_id.code')
    if any(country_code in ITSME_AVAILABLE_COUNTRIES for country_code in country_codes):
        # auto install localization module(s) if available
        module = env.ref('base.module_sign_itsme')
        if module:
            module.sudo().button_install()
