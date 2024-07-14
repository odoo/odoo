# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class HrApplicant(models.Model):
    _name = 'hr.applicant'
    _inherit = ['hr.applicant', 'documents.mixin']

    def _get_document_tags(self):
        return self.company_id.recruitment_tag_ids

    def _get_document_folder(self):
        return self.company_id.recruitment_folder_id

    def _get_document_partner(self):
        return self.partner_id

    def _check_create_documents(self):
        return self.company_id.documents_recruitment_settings and super()._check_create_documents()

    def action_open_attachments(self):
        if not self.company_id.documents_recruitment_settings:
            return super().action_open_attachments()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'documents.document',
            'name': _('Documents'),
            'view_mode': 'kanban,tree,form',
            'domain': [('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.ids)],
            'context': {
                'searchpanel_default_folder_id': self._get_document_folder().id,
                'default_res_model': 'hr.applicant',
                'default_res_id': self.ids[0],
            },
        }
