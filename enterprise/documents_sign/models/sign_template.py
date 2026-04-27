# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SignTemplate(models.Model):
    _name = 'sign.template'
    _inherit = ['sign.template', 'documents.unlink.mixin']

    folder_id = fields.Many2one('documents.document', 'Signed Document Folder',
                                context=lambda env: {
                                    'default_type': 'folder',
                                    'default_folder_id': env.company.documents_sign_folder_id.id,
                                },
                                domain="[('type', '=', 'folder'), ('shortcut_document_id', '=', False)]")
    documents_tag_ids = fields.Many2many('documents.tag', string="Signed Document Tags")

    @api.model_create_multi
    def create(self, vals_list):
        # In the super(), if an attachment is already attached to a record, a copy of the original attachment will be
        # created and used for the template. Here if the attachment is only used for Document, we directly reuse it for
        # the template by unlinking the relationships.
        self.env['ir.attachment'].browse([vals.get('attachment_id') for vals in vals_list])\
            .filtered(lambda att: att.res_model == 'documents.document')\
            .write({'res_model': False, 'res_id': 0})
        return super().create(vals_list)
