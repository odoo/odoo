# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard
from . import PYPDF2_MonkeyPatch

ITSME_AVAILABLE_COUNTRIES = [
    'BE', 'NL', 'AT', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE',
    'FR', 'DE', 'GR', 'HU', 'IS', 'IE', 'IT', 'LV', 'LT',
    'LU', 'MT', 'NO', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES',
    'SE', 'GB', 'FI'
]


def _sign_post_init(env):
    # check if any company is within itsme available countries
    country_codes = env['res.company'].search([]).mapped('country_id.code')
    if any(country_code in ITSME_AVAILABLE_COUNTRIES for country_code in country_codes):
        # auto install localization module(s) if available
        module = env.ref('base.module_sign_itsme')
        if module:
            module.sudo().button_install()


def uninstall_hook(env):
    # disable the a sign invoices while uninstalling a module
    if env['ir.module.module']._get('account_accountant').state == 'installed':
        env['res.company'].search([]).sign_invoice = False

    if env['ir.module.module']._get('documents').state == 'installed':
        document_query = env['documents.document']._search([('res_model', '=', 'sign.template')])
        mail_activities = env['mail.activity'].search([
            ('res_model', '=', 'documents.document'),
            ('res_id', 'in', document_query)
        ])
        mail_activities.unlink()
