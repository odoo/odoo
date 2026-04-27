# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_hr_settings = fields.Boolean()
    documents_hr_folder = fields.Many2one('documents.document', string="hr Workspace", check_company=True,
                                          domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)],
                                          compute='_compute_documents_hr_folder', store=True, readonly=False)

    @api.depends('documents_hr_settings')
    def _compute_documents_hr_folder(self):
        folder_id = self.env.ref('documents_hr.document_hr_folder', raise_if_not_found=False)
        self._reset_default_documents_folder_id('documents_hr_settings', 'documents_hr_folder', folder_id)

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [('documents_hr_folder', 'in', folder_ids), ('documents_hr_settings', '=', True)]
        ])
