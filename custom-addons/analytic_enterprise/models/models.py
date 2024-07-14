# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def grid_compute_year_range(self, anchor):
        result = self.env.company.compute_fiscalyear_dates(fields.Date.to_date(anchor))
        return {'date_from': result['date_from'], 'date_to': result['date_to']}
