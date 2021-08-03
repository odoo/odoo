# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def _get_journal_domain(self):
        default_company_id = self.default_get(['company_id'])['company_id']
        if self.env['res.company'].browse(default_company_id).country_id.code == 'CL':
            return [('type', '=', 'general'), ('company_id', '=', default_company_id)]
        return super()._get_journal_domain()
