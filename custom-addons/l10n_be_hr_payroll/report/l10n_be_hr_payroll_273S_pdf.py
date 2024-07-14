# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReportL10nBeHrPayroll273S(models.AbstractModel):
    _name = 'report.l10n_be_hr_payroll_273s_274.273s'
    _description = 'Get 273S report as PDF.'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': self.env['l10n_be.273s'],
            'data': data,
            'docs': self.env['l10n_be.273s'].browse(self.env.context.get('active_id')),
        }
