from . import models

import logging

_logger = logging.getLogger(__name__)


def _l10n_tr_nilvera_einvoice_extended_post_init(env):
    """Existing companies that have the Turkish Chart of Accounts set"""
    template_codes = ["tr"]
    tr_companies = env["res.company"].search(
        [("chart_template", "in", template_codes), ("parent_id", "=", False)]
    )
    for company in tr_companies:
        ChartTemplate = env["account.chart.template"].with_company(company)
        data = ChartTemplate._get_tr_withholding_account_tax()
        ChartTemplate._load_data({"account.tax": data})
