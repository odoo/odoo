# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_account_settings = fields.Boolean()
    account_folder_id = fields.Many2one(
        'documents.document', string="Accounting Workspace", check_company=True,
        compute='_compute_account_folder_id', store=True, readonly=False,
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)])

    @api.depends('documents_account_settings')
    def _compute_account_folder_id(self):
        folder_id = self.env.ref('documents.document_finance_folder', raise_if_not_found=False)
        self._reset_default_documents_folder_id('documents_account_settings', 'account_folder_id', folder_id)

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [('account_folder_id', 'in', folder_ids), ('documents_account_settings', '=', True)]
        ])
