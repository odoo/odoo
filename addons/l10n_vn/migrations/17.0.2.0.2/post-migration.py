from odoo import api, SUPERUSER_ID
from odoo.fields import Domain
from odoo.release import version
from odoo.tools import parse_version

FIXED_ACCOUNTS_TYPE = {
    'asset_prepayments': ['242'],
    'expense_depreciation': ['6274', '6414', '6424'],
}

def _fix_accounts_type(env):
    for correct_account_type, accounts_code in FIXED_ACCOUNTS_TYPE.items():
        domains_per_company = []
        for company in env['res.company'].with_context(active_test=False).search([('chart_template', '=', 'vn')]):
            if parse_version(version) > parse_version("saas~17.5"):
                company_domain = [('company_ids', 'in', company.ids), ('account_type', '!=', correct_account_type)]
            else:
                company_domain = [('company_id', '=', company.id), ('account_type', '!=', correct_account_type)]
            doamin = Domain.AND([company_domain, Domain.OR([[('code', 'like', f'{code}%')] for code in accounts_code])])
            domains_per_company.append(doamin)
        accounts = env['account.account'].search(Domain.OR(domains_per_company))
        accounts.account_type = correct_account_type


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_accounts_type(env)
