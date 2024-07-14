# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrPaylsip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'documents.mixin']

    def _get_document_tags(self):
        return self.company_id.documents_hr_payslips_tags

    def _get_document_owner(self):
        return self.employee_id.user_id

    def _get_document_partner(self):
        return self.employee_id.work_contact_id

    def _get_document_folder(self):
        return self.company_id.documents_payroll_folder_id

    def _check_create_documents(self):
        return self.company_id.documents_hr_settings and super()._check_create_documents()

    @api.model
    def _cron_generate_pdf(self, batch_size=False):
        is_rescheduled = super()._cron_generate_pdf(batch_size=batch_size)
        if is_rescheduled:
            return is_rescheduled

        # Post declarations from mixin
        lines = self.env['hr.payroll.employee.declaration'].search([('pdf_to_post', '=', True)])
        if lines:
            BATCH_SIZE = batch_size or 30
            lines_batch = lines[:BATCH_SIZE]
            lines_batch._post_pdf()
            lines_batch.write({'pdf_to_post': False})
            # if necessary, retrigger the cron to generate more pdfs
            if len(lines) > BATCH_SIZE:
                self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()
                return True
        return False
