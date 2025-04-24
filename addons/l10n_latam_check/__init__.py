from . import models
from . import wizards


def _post_init_hook(env):
    for company in env['res.company'].search([('parent_id', '=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'account.payment.method': ChartTemplate._get_latam_check_payment_methods(company.chart_template)
        })
