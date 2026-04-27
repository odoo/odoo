# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class HrApplicant(models.Model):
    _name = 'hr.applicant'
    _inherit = ['hr.applicant', 'documents.mixin']

    def _get_document_access_ids(self):
        access_ids = [
            (interviewer.partner_id, ('view', False))
            for interviewer in self.interviewer_ids
        ]
        if self.user_id and self.user_id not in self.interviewer_ids:
            access_ids.append((self.user_id.partner_id, ('view', False)))
        return access_ids

    def _get_document_tags(self):
        return self.company_id.recruitment_tag_ids

    def _get_document_folder(self):
        return self.company_id.recruitment_folder_id

    def _get_document_partner(self):
        return self.partner_id

    def _check_create_documents(self):
        return self.company_id.documents_recruitment_settings and super()._check_create_documents()

    def _get_document_vals_access_rights(self):
        vals = super()._get_document_vals_access_rights()
        if self.company_id.recruitment_folder_id:
            vals.update({
                'access_internal': self.company_id.recruitment_folder_id.access_internal,
                'access_via_link': self.company_id.recruitment_folder_id.access_via_link,
            })
        return vals

    def action_open_attachments(self):
        if not self.company_id.documents_recruitment_settings:
            return super().action_open_attachments()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'documents.document',
            'name': _('Documents'),
            'view_mode': 'kanban,list,form',
            'domain': [
                '|',
                    ('type', '=', 'folder'),
                    '&',
                        ('res_model', '=', 'hr.applicant'),
                        ('res_id', 'in', self.ids),
            ],
            'context': {
                'searchpanel_default_folder_id': self._get_document_folder().id,
                'default_res_model': 'hr.applicant',
                'default_res_id': self.ids[0],
            },
        }

    def write(self, vals):
        old_users = self.interviewer_ids | self.user_id
        res = super().write(vals)
        applicant_documents = self.env['documents.document'].search([
            ('res_model', '=', 'hr.applicant'),
            ('attachment_id', 'in', self.attachment_ids.ids),
        ])
        if not applicant_documents:
            return res
        new_users = self.interviewer_ids | self.user_id
        added_records = new_users - old_users
        removed_records = old_users - new_users
        partners_access = {
            record.partner_id.id: ('view', False) for record in added_records
        }
        partners_access.update({
            record.partner_id.id: (False, False) for record in removed_records
        })
        if partners_access:
            for document in applicant_documents:
                document.sudo().action_update_access_rights(
                    access_internal=document.access_internal,
                    access_via_link=document.access_via_link,
                    is_access_via_link_hidden=document.is_access_via_link_hidden,
                    partners=partners_access,
                )
        return res
