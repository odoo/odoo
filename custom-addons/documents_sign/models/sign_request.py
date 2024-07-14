# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SignRequest(models.Model):
    _name = 'sign.request'
    _inherit = ['sign.request', 'documents.mixin']

    def _get_document_tags(self):
        return self.template_id.documents_tag_ids

    def _get_document_folder(self):
        return self.template_id.folder_id
