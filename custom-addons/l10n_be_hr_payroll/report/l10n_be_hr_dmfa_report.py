# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportL10nBeHrDMFA(models.AbstractModel):
    _name = 'report.l10n_be_hr_payroll.dmfa_pdf_report'
    _description = 'Get DmfA declaration as PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids' : docids,
            'doc_model' : self.env['l10n_be.dmfa'],
            'data' : data,
            'docs' : self.env['l10n_be.dmfa'].browse(docids),
        }
