from . import models
from . import wizard


def post_init_hook(env):
    """ Define default journal for factoring invoices and create factoring receivable account,
    for every chilean company in the database"""
    for company in env['res.company'].search([('chart_template', '=', 'cl')]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        company_data = ChartTemplate._get_cl_res_company()
        ChartTemplate._load_data({'res.company': company_data})
