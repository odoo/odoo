# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SignTemplate(models.Model):
    _name = 'sign.template'
    _inherit = ['sign.template', 'documents.mixin']

    folder_id = fields.Many2one('documents.folder', 'Signed Document Workspace')
    documents_tag_ids = fields.Many2many('documents.tag', string="Signed Document Tags")

    @api.model_create_multi
    def create(self, vals_list):
        # In the super(), if an attachment is already attached to a record, a copy of the original attachment will be
        # created and used for the template. Here if the attachment is only used for Document, we directly reuse it for
        # the template by unlinking the relationships and call super() with_context no_document.
        self.env['ir.attachment'].browse([vals.get('attachment_id') for vals in vals_list])\
            .filtered(lambda att: att.res_model == 'documents.document')\
            .write({'res_model': False, 'res_id': 0})
        return super(SignTemplate, self.with_context(no_document=True))\
            .create(vals_list)\
            .with_context(no_document=bool(self._context.get('no_document')))

    def _get_document_tags(self):
        return self.documents_tag_ids

    def _get_document_folder(self):
        return self.folder_id
