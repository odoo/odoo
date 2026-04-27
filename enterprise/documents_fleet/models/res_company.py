# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_fleet_settings = fields.Boolean(default=True)
    documents_fleet_folder = fields.Many2one(
        'documents.document',
        string="Fleet Workspace",
        compute='_compute_documents_fleet_folder', store=True, readonly=False,
        domain="[('type', '=', 'folder'), ('shortcut_document_id', '=', False), '|', ('company_id', '=', False), ('company_id', '=', id)]",
    )
    documents_fleet_tags = fields.Many2many('documents.tag', 'documents_fleet_tags_table')

    @api.depends('documents_fleet_settings')
    def _compute_documents_fleet_folder(self):
        folder_id = self.env.ref('documents_fleet.document_fleet_folder', raise_if_not_found=False)
        self._reset_default_documents_folder_id('documents_fleet_settings', 'documents_fleet_folder', folder_id)

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [('documents_fleet_folder', 'in', folder_ids), ('documents_fleet_settings', '=', True)]
        ])
