from collections import defaultdict

from odoo import models


class StockValuationReport(models.AbstractModel):
    _inherit = "stock_account.stock.valuation.report"

    def _get_report_data(self, date=False, product_category=False):
        report_data = super()._get_report_data(
            date=date, product_category=product_category
        )
        if not self._is_cost_of_production_included():
            return report_data
        production_locations_valuation_vals = (
            self.env.company._prepare_location_valuation_vals(
                location_domain=[("usage", "=", "production")]
            )
        )
        cost_of_production = {
            "label": self.env._("Cost of Production"),
            "value": 0,
        }
        lines_by_account_id = defaultdict(
            lambda: {
                "debit": 0,
                "credit": 0,
                "lines": [],
            }
        )
        accounts = self.env["account.account"].browse(
            {vals["account_id"] for vals in production_locations_valuation_vals}
            - {False, None}
        )
        for account_vals in accounts.read(["name", "code", "display_name"]):
            report_data["accounts_by_id"][account_vals["id"]] = account_vals
        for vals in production_locations_valuation_vals:
            account_id = vals["account_id"]
            cost_of_production["value"] -= vals["debit"]
            lines_by_account_id[account_id]["debit"] += vals["debit"]
            lines_by_account_id[account_id]["credit"] += vals["credit"]
            lines_by_account_id[account_id]["lines"].append(vals)
        cost_of_production["lines"] = [
            {
                "account_id": account_id,
                "debit": vals["debit"],
                "credit": vals["credit"],
            }
            for (account_id, vals) in lines_by_account_id.items()
        ]
        report_data["cost_of_production"] = cost_of_production
        return report_data

    def _is_cost_of_production_included(self):
        return bool(
            self.env["stock.location"].search_count(
                [
                    ("usage", "=", "production"),
                    ("valuation_account_id", "!=", False),
                ],
                limit=1,
            )
        )


class StockValuationReportHandler(models.AbstractModel):
    _inherit = "stock_account.stock.valuation.report.handler"

    def _report_custom_engine_stock_valuation_cost_of_production(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._section_result("cost_of_production", options, current_groupby)

    def _section_move_usages(self):
        return {
            **super()._section_move_usages(),
            "SV_PRODUCTION": ("production", self.env._("Cost of Production")),
        }
