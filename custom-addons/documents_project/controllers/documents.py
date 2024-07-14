# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.addons.documents.controllers.documents import ShareRoute
from odoo.http import request

logger = logging.getLogger(__name__)


class ProjectShareRoute(ShareRoute):

    def _create_uploaded_documents(self, files, share, folder, documents_values=None):
        documents_values = documents_values or {}
        project = folder._get_project_from_closest_ancestor()
        if project:
            documents_values.update({
                'res_model': 'project.project',
                'res_id': project.id,
                'tag_ids': project.documents_tag_ids.ids,
            })
            if project.partner_id and not share.partner_id.id:
                documents_values['partner_id'] = project.partner_id.id
        return super()._create_uploaded_documents(files, share, folder, documents_values)

    @http.route()
    def upload_document(self, folder_id, ufile, tag_ids, **kwargs):
        if not kwargs.get('res_model') and not kwargs.get('res_id'):
            current_folder = request.env['documents.folder'].browse(int(folder_id))
            project = current_folder._get_project_from_closest_ancestor()
            if project:
                kwargs.update({
                    'res_model': 'project.project',
                    'res_id': project.id,
                })
                if project.partner_id:
                    kwargs['partner_id'] = project.partner_id.id
                if not tag_ids:
                    tag_ids = ','.join(str(tag_id) for tag_id in project.documents_tag_ids.ids)
        return super().upload_document(folder_id, ufile, tag_ids, **kwargs)
