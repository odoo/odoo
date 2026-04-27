# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_hr_payslips_tags = fields.Many2many(
        'documents.tag', 'payslip_tags_table')
    documents_payroll_folder_id = fields.Many2one(
        'documents.document', domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)],
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
        group_payroll_user = self.env.ref('hr_payroll.group_hr_payroll_user')
        parent_folder_id = self.env.ref('documents_hr.document_hr_folder', raise_if_not_found=False)

        folders = self.env["documents.document"].sudo().create([{
            'name': company.env._('Payroll'),
            'type': 'folder',
            'folder_id': parent_folder_id.id if parent_folder_id else False,
            'company_id': company.id,
        } for company in self])
        payslip_tag = self.env.ref('documents_hr_payroll.documents_tag_payslips', raise_if_not_found=False)
        for company, folder in zip(self, folders):
            company.write({
                'documents_hr_payslips_tags': [(6, 0, payslip_tag.ids)] if payslip_tag else [],
                'documents_payroll_folder_id': folder.id
            })
            payroll_users = group_payroll_user.users.filtered(lambda user: folder.company_id in user.company_ids)
            folder.action_update_access_rights(
                access_internal='view', access_via_link='none', is_access_via_link_hidden=True,
                partners={partner.id: ('edit', False) for partner in payroll_users.partner_id})

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [('documents_payroll_folder_id', 'in', folder_ids), ('documents_hr_settings', '=', True)]
        ])
