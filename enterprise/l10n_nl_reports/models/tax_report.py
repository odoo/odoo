from odoo import models


class DutchReportCustomHandler(models.AbstractModel):
    _name = 'l10n_nl.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Dutch Report Custom Handler'

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # OVERRIDE
        """ Apply the rounding from the Dutch tax report by adding a line to the end of the query results
            representing the sum of the roundings on each line of the tax report.
        """
        rounding_accounts = {
            'profit': company.l10n_nl_rounding_difference_profit_account_id,
            'loss': company.l10n_nl_rounding_difference_loss_account_id,
        }

        vat_results_summary = [
            ('total', self.env.ref('l10n_nl.tax_report_rub_btw_5g').id, 'balance'),
        ]

        return self._vat_closing_entry_results_rounding(company, options, results, rounding_accounts, vat_results_summary)
