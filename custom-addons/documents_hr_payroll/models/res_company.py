# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_hr_payslips_tags = fields.Many2many(
        'documents.tag', 'payslip_tags_table')
    documents_payroll_folder_id = fields.Many2one(
        'documents.folder',
        check_company=True)

    def _payroll_documents_enabled(self):
        self.ensure_one()
        return self.documents_payroll_folder_id and self.documents_hr_settings

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._generate_payroll_document_folders()
        return companies

    def _generate_payroll_document_folders(self):
        group_user = self.env.ref('base.group_user')
        group_payroll_user = self.env.ref('hr_payroll.group_hr_payroll_user')
        parent_folder_id = self.env.ref('documents_hr.documents_hr_folder', raise_if_not_found=False)

        folders = self.env["documents.folder"].sudo().create([{
            'name': _('Payroll'),
            'group_ids': [(4, group_payroll_user.id)],
            'read_group_ids': [(4, group_user.id)],
            'parent_folder_id': parent_folder_id.id if parent_folder_id else False,
            'user_specific': True,
            'sequence': 12,
            'company_id': company.id,
        } for company in self])

        payslip_tag = self.env.ref('documents_hr_payroll.documents_hr_documents_payslips', raise_if_not_found=False)
        for company, folder in zip(self, folders):
            company.write({
                'documents_hr_payslips_tags': [(6, 0, payslip_tag.ids)] if payslip_tag else [],
                'documents_payroll_folder_id': folder.id
            })
