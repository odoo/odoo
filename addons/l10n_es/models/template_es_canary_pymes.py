from odoo import _, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("es_canary_pymes")
    def _prepare_es_canary_pymes_template_data(self):
        return {
            "name": _("Canary Islands - SMEs (2008)"),
            "parent": "es_canary_common",
        }

    @template("es_canary_pymes", "res.company")
    def _get_es_canary_pymes_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.es",
                "bank_account_code_prefix": "572",
                "cash_account_code_prefix": "570",
                "transfer_account_code_prefix": "572999",
            },
        }

    @template("es_canary_pymes", "account.account")
    def _get_es_canary_pymes_account_account(self):
        res = self._prepare_csv_vals("es_pymes", "account.account", module="l10n_es")

        # Voluntarily remove the `tax_ids` since those are defined for the mainland and not the canaries
        for data in res.values():
            if "tax_ids" in data:
                del data["tax_ids"]

        return res

    @template("es_canary_pymes", "account.depreciation.profile")
    def _get_es_canary_pymes_account_depreciation_profile(self):
        # account_depreciation is not auto-installed when l10n_es is installed
        if "account.depreciation.profile" not in self.env:
            return {}
        return self._prepare_csv_vals(
            "es_pymes", "account.depreciation.profile", module="l10n_es"
        )
