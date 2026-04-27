from . import models


def _l10n_in_reports_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'in')]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'res.company': ChartTemplate._get_in_res_company_enterprise(company.chart_template),
        })
