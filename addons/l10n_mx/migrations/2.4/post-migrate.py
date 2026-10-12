from odoo import api, SUPERUSER_ID
from odoo.fields import Domain

FIXED_ACCOUNTS_TYPE = {
    'asset_fixed': ['171.02.01', '171.03.01', '171.04.01', '171.05.01', '171.16.01', '171.17.01', '171.18.01'],
    'asset_non_current': ['183.01.01', '183.07.01'],
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'mx')], order="parent_path"):
        for correct_account_type, accounts_codes in FIXED_ACCOUNTS_TYPE.items():
            domain = Domain.AND([
                [('company_ids', 'in', company.ids), ('account_type', '=', 'expense_depreciation')],
                Domain.OR([[('code', '=', code)] for code in accounts_codes]),
            ])
            accounts = env['account.account'].with_company(company).search(domain)
            accounts.account_type = correct_account_type
