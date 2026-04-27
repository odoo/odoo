from . import models


def _l10n_ee_rounding_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'ee')]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'res.company': ChartTemplate._get_ee_rounding_res_company(company.chart_template),
        })
