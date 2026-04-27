from . import models
from . import wizard


def _l10n_uk_reports_cis_post_init(env):
    cis_report = env.ref('l10n_uk_reports_cis.tax_report_cis')
    for company in env['res.company'].search([('chart_template', '=', 'uk'), ('parent_id', '=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'account.account': ChartTemplate._get_uk_account_account(),
            'account.tax': ChartTemplate._get_uk_account_tax(),
            'account.tax.group': ChartTemplate._get_uk_account_tax_group(),
        })

        # Replace the start date for the cis report
        cis_report.with_company(company).tax_closing_start_date = cis_report.with_company(company).tax_closing_start_date.replace(day=6)
