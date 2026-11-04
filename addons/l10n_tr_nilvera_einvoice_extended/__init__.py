import logging

from . import models

_logger = logging.getLogger(__name__)


def _l10n_tr_nilvera_einvoice_extended_post_init(env):
    """Existing none branch companies that have the Turkish Chart of Accounts set"""
    tr_companies = env["res.company"].search([("chart_template", "=", "tr"), ("parent_id", "=", False)], order="parent_path")
    for company in tr_companies:
        ChartTemplate = env["account.chart.template"].with_company(company)
        data = {
            "l10n_tr_nilvera_einvoice_extended.account.tax.code": ChartTemplate._get_tr_withholding_account_tax_code(),
            "account.tax": {
                xml_id: data
                for xml_id, data in ChartTemplate._get_tr_withholding_account_tax().items()
                if not env.ref(f"account.{company.id}_{xml_id}", raise_if_not_found=False)
            },
        }
        ChartTemplate._deref_account_tags("tr", data["account.tax"])
        ChartTemplate._pre_reload_data(company, {}, data)
        ChartTemplate._load_data(data)
        ChartTemplate._load_translations(companies=company)
