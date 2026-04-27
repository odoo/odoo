from odoo import models


class BalanceSheetCustomHandler(models.AbstractModel):
    _name = 'l10n_in_reports.balance.sheet.report.handler'
    _inherit = 'account.balance.sheet.report.handler'
    _description = 'Indian Custom Handler for Generic Balance Sheet'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        if (not previous_options or 'horizontal_split' not in previous_options or previous_options.get('companies') != options['companies']) \
            and self.env.company.chart_template == 'in':
            options['horizontal_split'] = False
