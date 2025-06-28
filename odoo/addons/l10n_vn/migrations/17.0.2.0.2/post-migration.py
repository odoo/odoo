from odoo import api, SUPERUSER_ID
from odoo.osv import expression

FIXED_ACCOUNTS_TYPE = {
    'asset_prepayments': ['242'],
    'expense_depreciation': ['6274', '6414', '6424'],
}


def _fix_accounts_type(env):
    for correct_account_type, accounts_code in FIXED_ACCOUNTS_TYPE.items():
        domains_per_company = []
        for company in env['res.company'].with_context(active_test=False).search([('chart_template', '=', 'vn')]):
            doamin = expression.AND([
                [('company_id', '=', company.id), ('account_type', '!=', correct_account_type)],
                expression.OR([
                    [('code', 'like', f'{code}%')] for code in accounts_code
                ])
            ])
            domains_per_company.append(doamin)
        accounts = env['account.account'].search(expression.OR(domains_per_company))
        accounts.account_type = correct_account_type


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_accounts_type(env)
