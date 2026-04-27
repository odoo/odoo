from . import models


def _post_init_hook_configure_corporate_tax_report_data(env):
    companies = env['res.company'].search([('account_fiscal_country_id.code', '=', 'AE')])
    env['account.chart.template']._l10n_ae_corporate_tax_report_setup_account_tags(companies)
