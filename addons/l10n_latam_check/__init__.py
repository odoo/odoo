from . import models
from . import wizards


def _post_init_hook(env):
    for company in env['res.company'].search([('parent_id', '=', False)]):
        if company.country_id.code == 'AR':
            ChartTemplate = env['account.chart.template'].with_company(company)
            ChartTemplate._load_data({
                'account.payment.method': ChartTemplate._get_latam_check_payment_methods(company.chart_template)
            })

            for bank_journal in env['account.journal'].search([('company_id', '=', company), ('type', '=', 'bank')]):
                bank_journal.outstanding_payment_account_id = env.ref('l10n_latam_check.base_outstanding_payments')
