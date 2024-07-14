# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DocumentMixin(models.AbstractModel):
    """
    Inherit this mixin to automatically create a `documents.document` when
    an `ir.attachment` is linked to a record.
    Override this mixin's methods to specify an owner, a folder or tags
    for the document.
    """
    _name = 'documents.mixin'
    _description = "Documents creation mixin"

    def _get_document_vals(self, attachment):
        """
        Return values used to create a `documents.document`
        """
        self.ensure_one()
        document_vals = {}
        if self._check_create_documents():
            document_vals = {
                'attachment_id': attachment.id,
                'name': attachment.name or self.display_name,
                'folder_id': self._get_document_folder().id,
                'owner_id': self._get_document_owner().id,
                'partner_id': self._get_document_partner().id,
                'tag_ids': [(6, 0, self._get_document_tags().ids)],
            }
        return document_vals

    def _get_document_owner(self):
        return self.env.user

    def _get_document_tags(self):
        return self.env['documents.tag']

    def _get_document_folder(self):
        return self.env['documents.folder']

    def _get_document_partner(self):
        return self.env['res.partner']

    def _check_create_documents(self):
        return bool(self and self._get_document_folder())
