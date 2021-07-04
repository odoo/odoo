JOURNALS_TO_CREATE = {"TA": {"name": "Tax Adjustments", "type": "general"},
                      "IFRS": {"name": "IFRS 16", "type": "general"}}


def create_journals(env):
    """"Create Tax Adjustments (TA) and IFRS 16 (IFRS) journals for all companies based in UAE if the journals do not already exist"""

    journals_to_create_code_set = set(JOURNALS_TO_CREATE.keys())
    ae_company_ids = set(env['res.company'].search([('partner_id.country_id.code', '=', 'AE')]).ids)
    journals = env['account.journal'].search(
        [('company_id', 'in', list(ae_company_ids)), ("code", "in", list(journals_to_create_code_set))])
    journals_dict = {company: set() for company in ae_company_ids}
    for journal in journals:
        journals_dict[journal.company_id.id] = {journal.code}.union(journals_dict[journal.company_id.id])
    for ae_company in ae_company_ids:
        for journal in journals_to_create_code_set - journals_dict[ae_company]:
            new_journal = env['account.journal'].create(
                {'company_id': ae_company, 'name': JOURNALS_TO_CREATE[journal]["name"],
                 'code': journal, 'type': JOURNALS_TO_CREATE[journal]["type"]})
            if journal == "IFRS":
                accounts = env['account.account'].search([('company_id', '=', ae_company),
                                                          ('code', 'in', (env.ref("l10n_ae.uae_account_100101").code,
                                                                          env.ref("l10n_ae.uae_account_100102").code,
                                                                          env.ref("l10n_ae.uae_account_400070").code))])
                for account in accounts:
                    account.allowed_journal_ids = [(4, new_journal.id, 0)]
