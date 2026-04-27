from odoo import models


class EstonianTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_ee.tax.report.handler'

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # OVERRIDE 'account_reports'
        """ Apply the rounding from the Estonian tax report to account for
        rounding differences between line-level tax calculations and the
        Estonian government's total tax computation (base_amount * tax_rate).
        """
        rounding_accounts = {
            'profit': company.l10n_ee_rounding_difference_profit_account_id,
            'loss': company.l10n_ee_rounding_difference_loss_account_id,
        }

        vat_results_summary = [
            ('due', self.env.ref('l10n_ee.tax_report_line_12').id, 'balance'),
            ('deductible', self.env.ref('l10n_ee.tax_report_line_13').id, 'balance'),
        ]

        return self._vat_closing_entry_results_rounding(company, options, results, rounding_accounts, vat_results_summary)
