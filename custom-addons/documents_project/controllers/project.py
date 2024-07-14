# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from odoo import http
from odoo.addons.documents.controllers.documents import ShareRoute
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

logger = logging.getLogger(__name__)


class DocumentsProjectShareRoute(http.Controller):

# ------------------------------------------------------------------------------
# Business methods
# ------------------------------------------------------------------------------

    def _check_access_and_get_task_from_project(self, project_id, task_id, access_token):
        CustomerPortal._document_check_access(self, 'project.project', project_id, access_token)
        return request.env['project.task'].sudo().search([('project_id', '=', project_id), ('id', '=', task_id)], limit=1)

    def _check_access_and_get_shared_documents(self, project_id=None, task_id=None, document_ids=None, access_token=None):
        if task_id and project_id:
            record_sudo = self._check_access_and_get_task_from_project(project_id, task_id, access_token)
        else:
            record_sudo = CustomerPortal._document_check_access(self, 'project.project' if project_id else 'project.task', project_id or task_id, access_token)

        documents = record_sudo.shared_document_ids
        if document_ids:
            documents = documents.filtered(lambda document: document.id in document_ids)
        if not documents:
            raise request.not_found()
        return documents

    def _get_document_owner_avatar(self, document):
        user_id = document.owner_id.id
        avatar = request.env['res.users'].sudo().browse(user_id).avatar_128

        if not avatar:
            return request.env['ir.http']._placeholder()
        return base64.b64decode(avatar)

# ------------------------------------------------------------------------------
# Project routes
# ------------------------------------------------------------------------------

    @http.route('/my/projects/<int:project_id>/documents', type='http', auth='public')
    def portal_my_project_documents(self, project_id, access_token=None, **kwargs):
        try:
            project_sudo = CustomerPortal._document_check_access(self, 'project.project', project_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        available_documents = project_sudo.shared_document_ids
        if not available_documents:
            return request.not_found()

        options = {
            'base_url': f"/my/projects/{project_id}/documents/",
            'upload': project_sudo.documents_folder_id.is_shared,
            'document_ids': available_documents,
            'all_button': len(available_documents) > 1 and 'binary' in available_documents.mapped('type'),
            'access_token': access_token,
        }
        return request.render('documents_project.share_page', options)

    @http.route('/my/projects/<int:project_id>/documents/<int:document_id>/thumbnail', type='http', auth='public')
    def portal_my_project_document_thumbnail(self, project_id, document_id, access_token=None, **kwargs):
        try:
            document = self._check_access_and_get_shared_documents(project_id, document_ids=[document_id], access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        try:
            return request.env['ir.binary']._get_stream_from(document, 'thumbnail').get_response()
        except Exception:
            return request.not_found()

    @http.route('/my/projects/<int:project_id>/documents/<int:document_id>/avatar', type='http', auth='public')
    def portal_my_project_document_avatar(self, project_id, document_id, access_token=None, **kwargs):
        try:
            document = self._check_access_and_get_shared_documents(project_id, document_ids=[document_id], access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        return self._get_document_owner_avatar(document)

    @http.route('/my/projects/<int:project_id>/documents/<int:document_id>/download', type='http', auth='public')
    def portal_my_project_documents_download(self, project_id, document_id, access_token=None, preview=None, **kwargs):
        try:
            document = self._check_access_and_get_shared_documents(project_id, document_ids=[document_id], access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        return request.env['ir.binary']._get_stream_from(document).get_response(as_attachment=not bool(preview))

    @http.route('/my/projects/<int:project_id>/documents/download', type='http', auth='public')
    def portal_my_project_documents_download_all(self, project_id, access_token=None, **kwargs):
        try:
            documents = self._check_access_and_get_shared_documents(project_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if not documents:
            raise request.not_found()

        project_name = request.env['project.project'].browse(project_id).name
        return ShareRoute._make_zip(project_name + '.zip', documents)

    @http.route('/my/projects/<int:project_id>/documents/upload', type='http', auth='public', methods=['POST'], csrf=False)
    def portal_my_project_document_upload(self, project_id, access_token=None, **kwargs):
        try:
            project_sudo = CustomerPortal._document_check_access(self, 'project.project', project_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        folder = project_sudo.documents_folder_id

        try:
            documents_vals = []
            for file in request.httprequest.files.getlist('files'):
                data = file.read()
                document_vals = {
                    'mimetype': file.content_type,
                    'name': file.filename,
                    'datas': base64.b64encode(data),
                    'partner_id': project_sudo.partner_id.id,
                    'owner_id': request.env.user.id,
                    'folder_id': folder.id,
                    'tag_ids': project_sudo.documents_tag_ids.ids,
                    'res_model': 'project.project',
                    'res_id': project_sudo.id,
                }
                documents_vals.append(document_vals)
            request.env['documents.document'].sudo().create(documents_vals)

        except Exception:
            logger.exception("Failed to upload document")

        token_string = f"access_token={access_token}" if access_token else ""
        return request.redirect(f"/my/projects/{project_id}/documents?" + token_string)

# ------------------------------------------------------------------------------
# Task routes
# ------------------------------------------------------------------------------

    @http.route([
        '/my/tasks/<int:task_id>/documents',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents',
    ], type='http', auth='public')
    def portal_my_task_documents(self, task_id, project_id=None, access_token=None, **kwargs):
        try:
            if project_id:
                task_sudo = self._check_access_and_get_task_from_project(project_id, task_id, access_token)
            else:
                task_sudo = CustomerPortal._document_check_access(self, 'project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        available_documents = task_sudo.shared_document_ids
        if not available_documents:
            return request.not_found()

        options = {
            'base_url': f"/my/projects/{project_id}/task/{task_id}/documents/" if project_id else f"/my/tasks/{task_id}/documents/",
            'upload': task_sudo.documents_folder_id.is_shared,
            'document_ids': available_documents,
            'all_button': len(available_documents) > 1 and 'binary' in available_documents.mapped('type'),
            'access_token': access_token,
        }
        return request.render('documents_project.share_page', options)

    @http.route([
        '/my/tasks/<int:task_id>/documents/<int:document_id>/thumbnail',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents/<int:document_id>/thumbnail',
    ], type='http', auth='public')
    def portal_my_task_document_thumbnail(self, task_id, document_id, project_id=None, access_token=None, **kwargs):
        try:
            document = self._check_access_and_get_shared_documents(project_id, task_id, [document_id], access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        try:
            return request.env['ir.binary']._get_stream_from(document, 'thumbnail').get_response()
        except Exception:
            return request.not_found()

    @http.route([
        '/my/tasks/<int:task_id>/documents/<int:document_id>/avatar',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents/<int:document_id>/avatar',
    ], type='http', auth='public')
    def portal_my_task_document_avatar(self, task_id, document_id, project_id=None, access_token=None, **kwargs):
        try:
            document = self._check_access_and_get_shared_documents(project_id, task_id, [document_id], access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        return self._get_document_owner_avatar(document)

    @http.route([
        '/my/tasks/<int:task_id>/documents/<int:document_id>/download',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents/<int:document_id>/download',
    ], type='http', auth='public')
    def portal_my_task_documents_download(self, task_id, document_id, project_id=None, access_token=None, preview=None, **kwargs):
        try:
            document = self._check_access_and_get_shared_documents(project_id, task_id, [document_id], access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        return request.env['ir.binary']._get_stream_from(document).get_response(as_attachment=not bool(preview))

    @http.route([
        '/my/tasks/<int:task_id>/documents/download',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents/download',
    ], type='http', auth='public')
    def portal_my_task_documents_download_all(self, task_id, project_id=None, access_token=None, **kwargs):
        try:
            documents = self._check_access_and_get_shared_documents(project_id, task_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if not documents:
            raise request.not_found()

        task_name = request.env['project.task'].sudo().browse(task_id).name
        return ShareRoute._make_zip(task_name + '.zip', documents)

    @http.route([
        '/my/tasks/<int:task_id>/documents/upload',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents/upload',
    ], type='http', auth='public', methods=['POST'], csrf=False)
    def portal_my_task_document_upload(self, task_id, project_id=None, access_token=None, **kwargs):
        try:
            if project_id:
                task_sudo = self._check_access_and_get_task_from_project(project_id, task_id, access_token)
            else:
                task_sudo = CustomerPortal._document_check_access(self, 'project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        folder = task_sudo.project_id.documents_folder_id

        try:
            documents_vals = []
            for file in request.httprequest.files.getlist('files'):
                data = file.read()
                document_vals = {
                    'mimetype': file.content_type,
                    'name': file.filename,
                    'datas': base64.b64encode(data),
                    'partner_id': task_sudo.partner_id.id,
                    'owner_id': request.env.user.id,
                    'folder_id': folder.id,
                    'tag_ids': task_sudo.project_id.documents_tag_ids.ids,
                    'res_model': 'project.task',
                    'res_id': task_sudo.id,
                }
                documents_vals.append(document_vals)
            request.env['documents.document'].sudo().create(documents_vals)

        except Exception:
            logger.exception("Failed to upload document")

        token_string = f"access_token={access_token}" if access_token else ""
        return request.redirect((f"/my/projects/{project_id}/task/{task_id}/documents/" if project_id else f"/my/tasks/{task_id}/documents/") + f"?{token_string}")
