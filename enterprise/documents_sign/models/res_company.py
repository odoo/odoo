# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_sign_folder_id = fields.Many2one('documents.document', string="Sign Folder", check_company=True,
                                            domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)],
                                            default=lambda self: self.env.ref('documents_sign.document_sign_folder',
                                                                              raise_if_not_found=False))
