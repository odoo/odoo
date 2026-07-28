from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    l10n_in_half_up_depreciated = env.ref('l10n_in.cash_rounding_in_half_up', raise_if_not_found=False)

    if l10n_in_half_up_depreciated:
        in_companies = env["res.company"].search([("account_fiscal_country_id.code", "=", "IN")])
        in_companies -= l10n_in_half_up_depreciated.company_id

        for company in in_companies:
            if env.ref(f'account.{company.id}_cash_rounding_in_half_up', raise_if_not_found=False):
                continue

            chart_template = env['account.chart.template'].with_company(company)
            profit_account = chart_template.ref('p213202', raise_if_not_found=False)
            loss_account = chart_template.ref('p213201', raise_if_not_found=False)
            rounding = env['account.cash.rounding'].with_company(company).create({
                'name': env._('Half Up'),
                'rounding': 1.00,
                'rounding_method': 'HALF-UP',
                'profit_account_id': profit_account.id if profit_account else False,
                'loss_account_id': loss_account.id if loss_account else False,
            })
            env['ir.model.data'].create({
                'name': f'{company.id}_cash_rounding_in_half_up',
                'module': 'account',
                'model': 'account.cash.rounding',
                'res_id': rounding.id,
                'noupdate': True,
            })
            env['account.move'].search([
                ('company_id', '=', company.id),
                ('invoice_cash_rounding_id', '=', l10n_in_half_up_depreciated.id),
            ]).invoice_cash_rounding_id = rounding

        l10n_in_half_up_depreciated.name = env._('Half Up')
        xmlid_data = env['ir.model.data'].search([
            ('module', '=', 'l10n_in'),
            ('name', '=', 'cash_rounding_in_half_up'),
        ])
        xmlid_data.write({
            'module': 'account',
            'name': f'{l10n_in_half_up_depreciated.company_id.id}_cash_rounding_in_half_up',
            'noupdate': True,
        })
