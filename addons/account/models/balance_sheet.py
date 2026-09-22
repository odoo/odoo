from odoo import models


class AccountBalanceSheetReportHandler(models.AbstractModel):
    _name = "account.balance.sheet.report.handler"
    _inherit = ["report.formula.custom.handler"]
    _description = "Balance Sheet Custom Handler"

    def _customize_warnings(
        self, report, options, all_column_groups_expression_totals, warnings
    ):
        if options["currency_table"]["type"] == "cta":
            warnings["account.common_possibly_unbalanced_because_cta"] = {}
