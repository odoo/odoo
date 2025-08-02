from . import models
from . import wizard


def _payment_bundle_post_init(env):
    """Existing companies that have the Argentinean Chart of Accounts set"""
    ar_companies = env["res.company"].search([("parent_id", "=", False)])
    for company in ar_companies:
        template_code = company.chart_template
        ChartTemplate = env["account.chart.template"].with_company(company)
        if journals_to_create := env["account.chart.template"]._get_payment_bundle_account_journal(template_code):
            ChartTemplate._load_data({"account.journal": journals_to_create})

