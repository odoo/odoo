# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from urllib.parse import quote

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.osv import expression
from odoo.tools.osutil import clean_filename

from odoo.addons.documents.controllers.documents import ShareRoute
from odoo.addons.portal.controllers.portal import CustomerPortal

logger = logging.getLogger(__name__)


class DocumentsProjectShareRoute(http.Controller):

# ------------------------------------------------------------------------------
# Business methods
# ------------------------------------------------------------------------------

    def _check_access_and_get_task_from_project(self, project_id, task_id, access_token):
        CustomerPortal._document_check_access(self, 'project.project', project_id, access_token)
        return request.env['project.task'].sudo().search([('project_id', '=', project_id), ('id', '=', task_id)], limit=1)

    def _get_project_project_documents(self, project):
        Task = request.env['project.task']
        return request.env['documents.document'].search(
            expression.OR([
                expression.AND([
                    [('res_model', '=', 'project.project')],
                    [('res_id', '=', project.id)]]),
                expression.AND([
                    [('res_model', '=', 'project.task')],
                    [('res_id', 'in', Task._search([('project_id', '=', project.id)]))],
                ]),
            ])
        )

# ------------------------------------------------------------------------------
# Project routes
# ------------------------------------------------------------------------------

    @http.route('/my/projects/<int:project_id>/documents', type='http', auth='user')
    def portal_my_project_documents(self, project_id, access_token=None, **kwargs):
        try:
            project_sudo = CustomerPortal._document_check_access(self, 'project.project', project_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        documents_sudo = self._get_project_project_documents(project_sudo)
        return request.render('documents_project.public_project_page', {
            'access_token': access_token or '',
            'project_id': project_id,
            'folder': project_sudo.documents_folder_id,
            'documents': documents_sudo,
            'subfolders': {},
            'quote': lambda v: quote(v, safe=''),
        })

    @http.route('/my/projects/<int:project_id>/documents/download', type='http', auth='user')
    def portal_my_project_documents_download_all(self, project_id, access_token=None, **kwargs):
        try:
            project_sudo = CustomerPortal._document_check_access(self, 'project.project', project_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        return ShareRoute()._make_zip(
            clean_filename(project_sudo.name) + '.zip',
            self._get_project_project_documents(project_sudo),
        )

    @http.route('/my/projects/<int:project_id>/documents/upload', type='http', auth='public', methods=['POST'])
    def portal_my_project_document_upload(self, project_id, access_token=None, **kwargs):
        try:
            project_sudo = CustomerPortal._document_check_access(self, 'project.project', project_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        folder = project_sudo.documents_folder_id
        if request.env.user.is_public:
            if folder.access_via_link != 'edit':
                return request.redirect('/my')
            owner = folder.owner_id
            partner = project_sudo.partner_id
        else:
            if folder.user_permission != 'edit':
                return request.redirect('/my')
            owner = request.env.user
            partner = request.env.user.partner_id

        ShareRoute()._documents_upload(
            folder,
            request.httprequest.files.getlist('ufile'),
            owner_id=owner.id,
            partner_id=partner.id,
            res_id=project_sudo.id,
            res_model='project.project',
        )
        return request.redirect_query(f'/my/projects/{project_id}/documents', {
            'access_token': access_token,
        })

# ------------------------------------------------------------------------------
# Task routes
# ------------------------------------------------------------------------------

    @http.route([
        '/my/tasks/<int:task_id>/documents',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents',
    ], type='http', auth='user')
    def portal_my_task_documents(self, task_id, project_id=None, access_token=None, **kwargs):
        try:
            if project_id:
                task_sudo = self._check_access_and_get_task_from_project(project_id, task_id, access_token)
            else:
                task_sudo = CustomerPortal._document_check_access(self, 'project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        documents_sudo = request.env['documents.document'].search([
            ('res_model', '=', 'project.task'),
            ('res_id', '=', task_sudo.id),
        ])
        return request.render('documents_project.public_task_page', {
            'access_token': access_token or '',
            'project_id': task_sudo.project_id.id,
            'task_id': task_sudo.id,
            'folder': task_sudo.project_id.documents_folder_id,
            'documents': documents_sudo,
            'subfolders': {},
            'quote': lambda v: quote(v, safe=''),
        })

    @http.route([
        '/my/tasks/<int:task_id>/documents/download',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents/download',
    ], type='http', auth='user')
    def portal_my_task_documents_download_all(self, task_id, project_id=None, access_token=None, **kwargs):
        try:
            if project_id:
                task_sudo = self._check_access_and_get_task_from_project(project_id, task_id, access_token)
            else:
                task_sudo = CustomerPortal._document_check_access(self, 'project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        return ShareRoute()._make_zip(
            clean_filename(task_sudo.name) + '.zip',
            request.env['documents.document'].search([
                ('res_model', '=', 'project.task'),
                ('res_id', '=', task_sudo.id),
            ]),
        )

    @http.route([
        '/my/tasks/<int:task_id>/documents/upload',
        '/my/projects/<int:project_id>/task/<int:task_id>/documents/upload',
    ], type='http', auth='public', methods=['POST'])
    def portal_my_task_document_upload(self, task_id, project_id=None, access_token=None, **kwargs):
        try:
            if project_id:
                task_sudo = self._check_access_and_get_task_from_project(project_id, task_id, access_token)
            else:
                task_sudo = CustomerPortal._document_check_access(self, 'project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        project_sudo = task_sudo.project_id
        folder = project_sudo.documents_folder_id

        if request.env.user.is_public:
            if folder.access_via_link != 'edit':
                return request.redirect('/my')
            owner = folder.owner_id
            partner = project_sudo.partner_id
        else:
            if folder.user_permission != 'edit':
                return request.redirect('/my')
            owner = request.env.user
            partner = request.env.user.partner_id

        ShareRoute()._documents_upload(
            folder,
            request.httprequest.files.getlist('ufile'),
            owner_id=owner.id,
            partner_id=partner.id,
            res_id=task_sudo.id,
            res_model='project.task',
        )

        url = f'/my/task/{task_sudo.id}/documents'
        if project_id:
            url = url.replace('/my', f'/my/projects/{project_id}')
        return request.redirect_query(url, {'access_token': access_token})
