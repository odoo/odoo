import logging

from . import models

_logger = logging.getLogger(__name__)


def _l10n_tr_nilvera_einvoice_extended_post_init(env):
    """Existing companies that have the Turkish Chart of Accounts set"""
    tr_companies = env["res.company"].search([("chart_template", "=", "tr")], order="parent_path")
    for company in tr_companies:
        chart_template = env["account.chart.template"].with_company(company)
        chart_template._load_data({
            "l10n_tr_nilvera_einvoice_extended.account.tax.code": chart_template._get_tr_withholding_account_tax_code(),
            "account.tax": {
                xml_id: data
                for xml_id, data in chart_template._get_tr_withholding_account_tax().items()
                if not env.ref(f"account.{company.id}_{xml_id}", raise_if_not_found=False)
            },
        })
        chart_template._load_translations(companies=company)
