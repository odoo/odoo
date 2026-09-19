from odoo import models, modules
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _get_account_reconcile_res_company(self, chart_template):
        company = self.env.company
        data = self._prepare_chart_template_data(chart_template)
        company_data = data["res.company"].get(company.id, {})

        required_data = {
            k: v for k, v in data.items() if k in ["account.journal", "account.account"]
        }
        self._pre_reload_data(company, data["template_data"], required_data)

        return {
            company.id: {
                "deferred_expense_journal_id": company.account_config_id.deferred_expense_journal_id.id
                or company_data.get("deferred_expense_journal_id"),
                "deferred_revenue_journal_id": company.account_config_id.deferred_revenue_journal_id.id
                or company_data.get("deferred_revenue_journal_id"),
                "deferred_expense_account_id": company.account_config_id.deferred_expense_account_id.id
                or company_data.get("deferred_expense_account_id"),
                "deferred_revenue_account_id": company.account_config_id.deferred_revenue_account_id.id
                or company_data.get("deferred_revenue_account_id"),
            }
        }

    @_debug.perf.timed
    def _prepare_chart_template_data(self, chart_template):
        data = super()._prepare_chart_template_data(chart_template)

        for company_data in data["res.company"].values():
            company_data["deferred_expense_journal_id"] = company_data.get(
                "deferred_expense_journal_id"
            ) or next(
                (
                    xid
                    for xid, d in data["account.journal"].items()
                    if d["type"] == "general"
                ),
                None,
            )

            company_data["deferred_revenue_journal_id"] = company_data.get(
                "deferred_revenue_journal_id"
            ) or next(
                (
                    xid
                    for xid, d in data["account.journal"].items()
                    if d["type"] == "general"
                ),
                None,
            )

            company_data["deferred_expense_account_id"] = company_data.get(
                "deferred_expense_account_id"
            ) or next(
                (
                    xid
                    for xid, d in data["account.account"].items()
                    if d["account_type"] == "asset_current"
                ),
                None,
            )

            company_data["deferred_revenue_account_id"] = company_data.get(
                "deferred_revenue_account_id"
            ) or next(
                (
                    xid
                    for xid, d in data["account.account"].items()
                    if d["account_type"] == "liability_current"
                ),
                None,
            )
            _debug.logic(
                "deferred_defaults_resolved",
                chart=chart_template,
                expense_journal=company_data.get("deferred_expense_journal_id"),
                revenue_journal=company_data.get("deferred_revenue_journal_id"),
                expense_account=company_data.get("deferred_expense_account_id"),
                revenue_account=company_data.get("deferred_revenue_account_id"),
            )

        return data

    @_debug.perf.timed
    def _post_load_data(self, template_code, company, template_data):
        _debug.lifecycle("_post_load_data", records=self)
        super()._post_load_data(template_code, company, template_data)

        sepa_countries = self.env.ref("base.sepa_zone").country_ids
        if _debug.logic.enabled:
            _debug.logic(
                "sepa_zone_checked",
                company=company,
                in_sepa=company.country_id in sepa_countries,
            )
        if company.country_id in sepa_countries:
            sepa_module = (
                self.env["ir.module.module"]
                .sudo()
                .search([("name", "=", "account_iso20022")], limit=1)
            )
            if sepa_module and sepa_module.state != "installed":
                if _debug.logic.enabled:
                    _debug.logic(
                        "sepa_module_install_mode",
                        company=company,
                        module=sepa_module,
                        immediate=bool(
                            self.env.registry.ready
                            and not modules.module.current_test
                            and not self.env.context.get("install_demo")
                        ),
                    )
                if (
                    self.env.registry.ready
                    and self.env.registry.ready
                    and not modules.module.current_test
                    and not self.env.context.get("install_demo")
                ):
                    sepa_module.button_immediate_install()
                else:
                    sepa_module.button_install()
