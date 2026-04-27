from . import models


def _l10n_ae_reports_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'ae')], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'res.company': ChartTemplate._get_ae_reports_res_company(company.chart_template),
        })
