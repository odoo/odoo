from odoo import SUPERUSER_ID, api


def link_ifrs_accounts_to_ifrs16_journal(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ae_company_ids = env['res.company'].search([('partner_id.country_id.code', '=', 'AE')]).ids
    for ae_company in ae_company_ids:
        ifrs_journal = env['account.journal'].search([('company_id', '=', ae_company), ('code', '=', 'IFRS')]).id
        accounts = env['account.account'].search([('company_id', '=', ae_company),
                                                  ('code', 'in', (env.ref("l10n_ae.uae_account_100101").code,
                                                                  env.ref("l10n_ae.uae_account_100102").code,
                                                                  env.ref("l10n_ae.uae_account_400070").code))])
        for account in accounts:
            account.allowed_journal_ids = [(4, ifrs_journal, 0)]
