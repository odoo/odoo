# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

FIXED_ACCOUNTS_MAP = {
    '5221': '5211',
    '5222': '5212',
    '5223': '5213'
    }


def _fix_revenue_deduction_accounts_code(env):
    vn_template = env.ref('l10n_vn.vn_template')
    for company in env['res.company'].with_context(active_test=False).search([('chart_template_id', '=', vn_template.id)]):
        for incorrect_code, correct_code in FIXED_ACCOUNTS_MAP.items():
            account = env['account.account'].search([('code', '=', incorrect_code), ('company_id', '=', company.id)])
            if account:
                account.write({'code': correct_code})


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_revenue_deduction_accounts_code(env)
