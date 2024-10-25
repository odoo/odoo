from odoo import api, SUPERUSER_ID
from odoo.osv import expression

FIXED_TYPE_CODES_MAP = {
    'expense_direct_cost': ('6271', '6272', '6273', '6274', '6277', '6278'),
}


def _fix_accounts_type(env):
    vn_companies = env['res.company'].with_context(active_test=False).search([('chart_template_id', '=', env.ref('l10n_vn.vn_template').id)])
    for correct_account_type, account_codes in FIXED_TYPE_CODES_MAP.items():
        accounts = env['account.account'].search([
            ('company_id', 'in', vn_companies.ids),
            ('account_type', '!=', correct_account_type),
            expression.OR([
                [('code', '=like', f'{code}%')]
                for code in account_codes
            ]),
        ])
        accounts.write({
            'account_type': correct_account_type
        })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_accounts_type(env)
