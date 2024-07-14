from odoo import models

class BelgianTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_be.tax.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        if previous_options:
            options.update({
                'closing_entry': previous_options.get('closing_entry'),
                'ask_restitution': previous_options.get('ask_restitution'),
                'ask_payment': previous_options.get('ask_payment'),
                'client_nihil': previous_options.get('client_nihil'),
            })
