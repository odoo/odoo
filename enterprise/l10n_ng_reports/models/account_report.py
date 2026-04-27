# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class NigerianTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ng.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Nigerian Tax Report Custom Handler'

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        if warnings is not None and options['date']['period_type'] != 'month':
            warnings['l10n_ng_reports.tax_report_period_check'] = {
                'warning_message': _("Choose a month in the filter to display the VAT report correctly."),
                'alert_type': 'warning',
            }


class NigerianWithholdingReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ng.withholding.report.handler'
    _inherit = 'l10n_ng.tax.report.handler'
    _description = 'Nigerian Withholding Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        # closing entry button shouldn't be visible in the withholding reports
        options['buttons'] = [button for button in options['buttons'] if button['action'] != 'action_periodic_vat_entries']
