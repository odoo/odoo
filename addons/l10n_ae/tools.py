JOURNALS_TO_CREATE = {"TA": {"name": "Tax Adjustments", "type": "general"},
                      "IFRS": {"name": "IFRS 16", "type": "general"}}


def create_journals(env):
    journals_to_create_code_set = set(JOURNALS_TO_CREATE.keys())
    ae_company_ids = set(map(lambda rec: rec["id"],
                             env['res.company'].search_read(domain=[('partner_id.country_id.code', '=', 'AE')],
                                                            fields=['id'])))
    journals = env['account.journal'].search_read(
        domain=[('company_id', 'in', list(ae_company_ids)), ("code", "in", list(journals_to_create_code_set))],
        fields=["company_id", "code"])
    journals_dict = {company: set() for company in ae_company_ids}
    for journal in journals:
        journals_dict[journal["company_id"][0]] = {journal["code"]}.union(journals_dict[journal["company_id"][0]])
    for ae_company in ae_company_ids:
        for journal in journals_to_create_code_set - journals_dict[ae_company]:
            new_journal = env['account.journal'].create(
                {'company_id': ae_company, 'name': JOURNALS_TO_CREATE[journal]["name"],
                 'code': journal, 'type': JOURNALS_TO_CREATE[journal]["type"]})
            if journal == "IFRS":
                accounts = env['account.account'].search([('company_id', '=', ae_company),
                                               ('code', 'in', (env.ref("l10n_ae.uae_account_3665").code,
                                                               env.ref("l10n_ae.uae_account_3666").code,
                                                               env.ref("l10n_ae.uae_account_3806").code))])
                for account in accounts:
                    account.allowed_journal_ids = [(4, new_journal.id, 0)]
            if journal == "TA":
                env["res.config.settings"].account_tax_periodicity_journal_id = new_journal.id
