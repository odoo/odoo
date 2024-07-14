# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportL10nBeHrPayrollSocialBalance(models.AbstractModel):
    _name = 'report.l10n_be_hr_payroll.report_social_security_certificate'
    _description = 'Get Social Security Certificate as PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids' : docids,
            'doc_model' : self.env['l10n.be.social.security.certificate'],
            'data' : data,
            'docs' : self.env['l10n.be.social.security.certificate'].browse(docids),
        }
