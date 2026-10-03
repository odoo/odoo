from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Create the e-reporting journal for FR companies where PDP is already enabled."""
    env = api.Environment(env.cr, SUPERUSER_ID, {})
    Company = env['res.company']

    companies = Company.search([
        ('country_code', '=', 'FR'),
        ('l10n_fr_pdp_enabled', '=', True),
    ])
    companies._l10n_fr_pdp_ensure_journal()
