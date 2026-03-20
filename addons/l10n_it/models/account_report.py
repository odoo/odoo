# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountReportExpression(models.AbstractModel):
    _inherit = "account.report.expression"

    def _get_carryover_target_expression(self, options):
        if self.report_line_id.code == 'VP14' and fields.Date.from_string(options['date']['date_to']).month == 12:
            # For this line, if we are between two years, we want to carry over to vp9 instead of the line set in the XML file (vp8)
            return self.env.ref('l10n_it.tax_monthly_report_line_vp9_applied_carryover')

        return super()._get_carryover_target_expression(options)
