# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_approvals_settings = fields.Boolean(default=False)
    approvals_folder_id = fields.Many2one(
        'documents.document',
        string="Approvals Workspace",
        compute='_compute_approvals_folder_id', store=True, readonly=False,
        check_company=True,
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)],
    )
    approvals_tag_ids = fields.Many2many('documents.tag', 'approvals_tags_rel')

    @api.depends('documents_approvals_settings')
    def _compute_approvals_folder_id(self):
        folder_id = self.env.ref('documents_approvals.document_approvals_folder', raise_if_not_found=False)
        self._reset_default_documents_folder_id('documents_approvals_settings', 'approvals_folder_id', folder_id)

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [('approvals_folder_id', 'in', folder_ids), ('documents_approvals_settings', '=', True)]
        ])
