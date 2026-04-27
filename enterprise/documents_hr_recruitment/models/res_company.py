# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_recruitment_settings = fields.Boolean(default=False)
    recruitment_folder_id = fields.Many2one('documents.document', string="Recruitment Workspace", check_company=True,
                                            domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)],
                                            compute='_compute_recruitment_folder_id', store=True, readonly=False)
    recruitment_tag_ids = fields.Many2many('documents.tag', 'recruitment_tags_rel')

    @api.depends('documents_recruitment_settings')
    def _compute_recruitment_folder_id(self):
        folder_id = self.env.ref('documents_hr_recruitment.document_recruitment_folder', raise_if_not_found=False)
        self._reset_default_documents_folder_id('documents_recruitment_settings', 'recruitment_folder_id', folder_id)

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [('recruitment_folder_id', 'in', folder_ids), ('documents_recruitment_settings', '=', True)]
        ])
