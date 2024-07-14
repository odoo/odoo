# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class L10nBeSocialBalanceSheet(models.TransientModel):
    _inherit = 'l10n.be.social.balance.sheet'

    def _post_process_generated_file(self, data, filename):
        if self.company_id.documents_payroll_folder_id and self.company_id.documents_hr_settings:
            self.env['documents.document'].create({
                'owner_id': False,
                'datas': data,
                'name': filename,
                'folder_id': self.company_id.documents_payroll_folder_id.id,
                'res_model': 'hr.payslip',  # Security Restriction to payroll managers
            })
        return super()._post_process_generated_file(data, filename)
