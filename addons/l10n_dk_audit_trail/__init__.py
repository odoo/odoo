def _l10n_dk_audit_trail_post_init(env):
    dk_companies = env['res.company'].search([
        ('partner_id.country_id.code', '=', 'DK'),
        ('check_account_audit_trail', '=', False),
    ])
    if dk_companies:
        dk_companies.write({'check_account_audit_trail': True})
