from . import models


def _l10n_in_tcs_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'in'), ('parent_id', '=', False)]):
        env['res.company']._l10n_in_load_tcs_chart_of_accounts_and_taxes(company)
