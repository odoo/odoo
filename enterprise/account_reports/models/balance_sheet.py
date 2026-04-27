from odoo import models


class BalanceSheetCustomHandler(models.AbstractModel):
    _name = 'account.balance.sheet.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = "Balance Sheet Custom Handler"

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        if options['currency_table']['type'] == 'cta':
            warnings['account_reports.common_possibly_unbalanced_because_cta'] = {}
