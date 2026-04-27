# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_product_settings = fields.Boolean()
    product_folder_id = fields.Many2one(
        'documents.document', string="Product Workspace", check_company=True,
        compute='_compute_product_folder_id', store=True, readonly=False,
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)])
    product_tag_ids = fields.Many2many('documents.tag', 'product_tags_table')

    @api.depends('documents_product_settings')
    def _compute_product_folder_id(self):
        folder_id = self.env.ref('documents_product.document_product_folder', raise_if_not_found=False)
        self._reset_default_documents_folder_id('documents_product_settings', 'product_folder_id', folder_id)

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [('product_folder_id', 'in', folder_ids), ('documents_product_settings', '=', True)]
        ])
