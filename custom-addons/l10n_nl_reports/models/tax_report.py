# -*- coding: utf-8 -*-
from odoo import models

class DutchReportCustomHandler(models.AbstractModel):
    _name = 'l10n_nl.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Dutch Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        self.env['account.report'].browse(options['report_id'])._custom_options_add_integer_rounding(options, 'DOWN', previous_options=previous_options)
