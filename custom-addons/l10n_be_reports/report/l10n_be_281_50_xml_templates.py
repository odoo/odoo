# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportL10nBeXMLReports28150(models.AbstractModel):
    _name = 'report.l10n_be_reports.report_281_50_xml'
    _description = 'Get 281.50 report as XML.'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': self.env['l10n_be.form.325'],
            'data': data,
            'docs': docids,
        }
