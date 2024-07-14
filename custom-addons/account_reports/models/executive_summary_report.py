# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError

class ExecutiveSummaryReport(models.Model):
    _inherit = 'account.report'

    def _report_custom_engine_executive_summary_ndays(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        if current_groupby or next_groupby:
            raise UserError("NDays expressions of executive summary report don't support the 'group by' feature.")

        date_diff = fields.Date.from_string(options['date']['date_to']) - fields.Date.from_string(options['date']['date_from'])
        return {'result': date_diff.days}
