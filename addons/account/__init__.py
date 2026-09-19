def _set_fiscal_country(env):
    env["account.config"]._for_each(
        env["res.company"].search([])
    )._compute_account_fiscal_country_id()


def _load_deferred_accounts(env):
    for company in env["res.company"].search([], order="parent_path"):
        if not company.account_config_id.chart_template:
            continue
        ChartTemplate = env["account.chart.template"].with_company(company)
        ChartTemplate._load_data(
            {
                "res.company": ChartTemplate._get_account_reconcile_res_company(
                    company.account_config_id.chart_template
                ),
            }
        )


def _install_sepa_modules(env):
    companies = env["res.company"].search([])
    if not any(
        company.country_id and "SEPA" in company.country_id.country_group_codes
        for company in companies
    ):
        return
    env["ir.module.module"].search(
        [
            ("name", "in", ["account_iso20022", "account_bank_statement_import_camt"]),
            ("state", "=", "uninstalled"),
        ]
    ).sudo().button_install()


def _load_account_return_data(env):
    env.ref("account.ir_cron_generate_account_return")._trigger()

    env["account.return.type"].search([])._set_default_values(
        env["res.company"].search([])
    )

    for company in env["res.company"].search(
        [("account_config_id.chart_template", "!=", False)], order="parent_path"
    ):
        ChartTemplate = env["account.chart.template"].with_company(company)
        # Set up the tax returns journal after the CoA was already installed.
        ChartTemplate._load_data(
            {
                "account.journal": ChartTemplate._get_account_reports_journal(
                    company.account_config_id.chart_template
                ),
                "res.company": ChartTemplate._get_account_reports_res_company(
                    company.account_config_id.chart_template
                ),
            }
        )


def _account_post_init(env):
    _set_fiscal_country(env)
    _install_sepa_modules(env)
    _load_deferred_accounts(env)
    _load_account_return_data(env)


from . import controllers
from . import models
from . import demo
from . import wizards
from . import reports
from . import tools
