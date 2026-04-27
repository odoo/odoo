# -*- coding: utf-8 -*-

import base64
import io
import json
import logging
import pathlib
import zipfile
from collections import defaultdict
from contextlib import ExitStack
from http import HTTPStatus
from typing import NamedTuple
from urllib.parse import quote

from werkzeug.exceptions import BadRequest, Forbidden

from odoo import conf, fields, http, _
from odoo.exceptions import MissingError
from odoo.http import request, content_disposition
from odoo.osv import expression
from odoo.tools import replace_exceptions, str2bool, consteq

from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.mail.controllers.attachment import AttachmentController

logger = logging.getLogger(__name__)


class ShareRoute(http.Controller):

    # util methods #################################################################################
    def _max_content_length(self):
        return request.env['documents.document'].get_document_max_upload_limit()

    @classmethod
    def _get_folder_children(cls, folder_sudo):
        if request.env.user._is_public():
            permission_domain = expression.AND([
                [('is_access_via_link_hidden', '=', False)],
                [('access_via_link', 'in', ('edit', 'view'))],
                # public user cannot access a request, unless access_via_link='edit'
                expression.OR([
                    [('access_via_link', '=', 'edit')],
                    [('type', '!=', 'binary')],
                    expression.OR([
                        [('attachment_id', '!=', False)],
                        [('shortcut_document_id.attachment_id', '!=', False)],
                    ]),
                ])
            ])
        else:
            permission_domain = [('user_permission', '!=', 'none')]  # needed for search in sudo

        children_sudo = request.env['documents.document'].sudo().search(expression.AND([
            [('folder_id', '=', folder_sudo.id)],
            permission_domain,
        ]), order='name')

        return children_sudo

    @classmethod
    def _from_access_token(cls, access_token, *, skip_log=False, follow_shortcut=True):
        """Get existing document with matching ``access_token``.

        It returns an empty recordset when either:
        * the document is not found ;
        * the user cannot already access the document and the link
          doesn't grant access ;
        * the matching document is a shortcut but it is not allowed to
          follow the shortcut.
        Otherwise it returns the matching document in sudo.

        A ``documents.access`` record is created/updated with the
        current date unless the ``skip_log`` flag is set.

        :param str access_token: the access token to the document record
        :param bool skip_log: flag to prevent updating the record last
            access date of internal users, useful to prevent silly
            serialization errors, best used with read-only controllers.
        :param bool follow_shortcut: flag to prevent returning the target
            from a shortcut and instead return the shortcut itself.
        """
        Doc = request.env['documents.document']

        # Document record
        try:
            document_token, __, encoded_id = access_token.rpartition('o')
            document_id = int(encoded_id, 16)
        except ValueError:
            return Doc
        if not document_token or document_id < 1:
            return Doc
        document_sudo = Doc.browse(document_id).sudo()
        try:
            if not document_sudo.document_token: # like exists() but prefetch 
                return Doc
        except MissingError:
            return Doc

        # Permissions
        if not (
            consteq(document_token, document_sudo.document_token)
            and (document_sudo.user_permission != 'none'
                 or document_sudo.access_via_link != 'none')
        ):
            return Doc
        if not request.env.user._is_internal() and not document_sudo.active:
            return Doc

        # Document access
        skip_log = skip_log or request.env.user._is_public()
        if not skip_log:
            for doc_sudo in filter(bool, (document_sudo, document_sudo.shortcut_document_id)):
                if access := request.env['documents.access'].sudo().search([
                    ('partner_id', '=', request.env.user.partner_id.id),
                    ('document_id', '=', doc_sudo.id),
                ]):
                    access.last_access_date = fields.Datetime.now()
                else:
                    if doc_sudo._get_permission_without_token() == 'none':
                        # Used to trigger webclient reload
                        document_sudo = document_sudo.with_context(document_newly_accessible=True)
                    request.env['documents.access'].sudo().create([{
                        'document_id': doc_sudo.id,
                        'partner_id': request.env.user.partner_id.id,
                        'last_access_date': fields.Datetime.now(),
                    }])

        # Shortcut
        if follow_shortcut:
            if target_sudo := document_sudo.shortcut_document_id:
                if (target_sudo.user_permission != 'none'
                    or (target_sudo.access_via_link != 'none'
                        and not target_sudo.is_access_via_link_hidden)):
                    document_sudo = target_sudo
                else:
                    document_sudo = Doc

        # Extra validation step, to run with the target
        if (
            request.env.user._is_public()
            and document_sudo.type == 'binary'
            and not document_sudo.attachment_id
            and document_sudo.access_via_link != 'edit'
        ):
            # public cannot access a document request, unless access_via_link='edit'
            return Doc

        return document_sudo

    def _make_zip(self, name, documents):
        """
        Create a zip file in memory out of the given ``documents``,
        recursively exploring the folders, get an HTTP response to
        download that zip file.

        :param str name: the name to give to the zip file
        :param odoo.models.Model documents: documents to load in the ZIP
        :return: a http response to download the zip file
        """
        class Item(NamedTuple):
            path: str
            content: str

        seen_folders = set()  # because of shortcuts, we can have loops
        # many documents can have the same name
        seen_names = defaultdict(int)

        def unique(pathname):
            # files inside a zip can not have the same name
            # (files in the documents application can)
            seen_names[pathname] += 1
            if seen_names[pathname] <= 1:
                return pathname

            ext = ''.join(pathlib.Path(pathname).suffixes)
            return f'{pathname.removesuffix(ext)}-{seen_names[pathname]}{ext}'

        def make_zip_item(document, folder):
            if document.type == 'url':
                raise ValueError("cannot create a zip item out of an url")
            if document.type == 'folder':
                document_name = document.name.replace('/', '_')
                # it is the ending slash that makes it appears as a
                # folder inside the zip file.
                return Item(unique(f'{folder.path}{document_name}') + '/', '')
            try:
                stream = self._documents_content_stream(document.shortcut_document_id or document)
                download_name = stream.download_name.replace('/', '_')
            except (ValueError, MissingError):
                return None  # skip
            return Item(unique(f'{folder.path}{download_name}'), stream.read())

        def generate_zip_items(documents_sudo, folder):
            documents_sudo = documents_sudo.sorted(lambda d: d.id)

            yield from (
                item
                for doc in documents_sudo
                if doc.type == 'binary' and (doc.shortcut_document_id or doc).attachment_id
                if (item := make_zip_item(doc, folder)) is not None
            )
            for folder_sudo in documents_sudo:
                if folder_sudo.type != 'folder' or folder_sudo in seen_folders:
                    continue
                seen_folders.add(folder_sudo)

                yield (sub_folder := make_zip_item(folder_sudo, folder))
                for sub_document_sudo in self._get_folder_children(folder_sudo):
                    yield from generate_zip_items(sub_document_sudo, sub_folder)

        # TODO: zip on-the-fly while streaming instead of loading the
        #       entire zip in memory and sending it all at once.

        stream = io.BytesIO()
        root_folder = Item('', '')
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                for (path, content) in generate_zip_items(documents, root_folder):
                    doc_zip.writestr(path, content, compress_type=zipfile.ZIP_DEFLATED)
        except zipfile.BadZipfile:
            logger.exception("BadZipfile exception")

        content = stream.getvalue()
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(name))
        ]
        return request.make_response(content, headers)

    # Download & upload routes #####################################################################
    @http.route('/documents/pdf_split', type='http', methods=['POST'], auth="user")
    def pdf_split(self, new_files=None, ufile=None, archive=False, vals=None):
        """Used to split and/or merge pdf documents.

        The data can come from different sources: multiple existing documents
        (at least one must be provided) and any number of extra uploaded files.

        :param new_files: the array that represents the new pdf structure:
            [{
                'name': 'New File Name',
                'new_pages': [{
                    'old_file_type': 'document' or 'file',
                    'old_file_index': document_id or index in ufile,
                    'old_page_number': 5,
                }],
            }]
        :param ufile: extra uploaded files that are not existing documents
        :param archive: whether to archive the original documents
        :param vals: values for the create of the new documents.
        """
        vals = json.loads(vals)
        new_files = json.loads(new_files)
        # find original documents
        document_ids = set()
        for new_file in new_files:
            for page in new_file['new_pages']:
                if page['old_file_type'] == 'document':
                    document_ids.add(page['old_file_index'])
        documents = request.env['documents.document'].browse(document_ids)
        documents.check_access('read')

        with ExitStack() as stack:
            files = request.httprequest.files.getlist('ufile')
            open_files = [stack.enter_context(io.BytesIO(file.read())) for file in files]

            # merge together data from existing documents and from extra uploads
            document_id_index_map = {}
            current_index = len(open_files)
            for document in documents:
                open_files.append(stack.enter_context(io.BytesIO(base64.b64decode(document.datas))))
                document_id_index_map[document.id] = current_index
                current_index += 1

            # update new_files structure with the new indices from documents
            for new_file in new_files:
                for page in new_file['new_pages']:
                    if page.pop('old_file_type') == 'document':
                        page['old_file_index'] = document_id_index_map[page['old_file_index']]

            # apply the split/merge
            new_documents = documents._pdf_split(new_files=new_files, open_files=open_files, vals=vals)

        # archive original documents if needed
        if archive == 'true':
            documents.write({'active': False})

        response = request.make_response(json.dumps(new_documents.ids), [('Content-Type', 'application/json')])
        return response

    @http.route('/documents/<access_token>', type='http', auth='public')
    def documents_home(self, access_token):
        document_sudo = self._from_access_token(access_token)

        member_signup_token = request.params.get('member_signup_token')
        member_id = int(request.params.get('member_id') or "0")

        if not document_sudo:
            Redirect = request.env['documents.redirect'].sudo()
            if document_sudo := Redirect._get_redirection(access_token):
                return request.redirect(
                    f'/documents/{quote(document_sudo.access_token, safe="")}?{keep_query("*")}',
                    HTTPStatus.MOVED_PERMANENTLY,
                )

        if request.env.user._is_public():
            if not document_sudo:
                redirect_url = f'/documents/{quote(access_token, safe="")}?{keep_query("*")}'
                if signup_url := request.env["documents.access"]._get_signup_url(
                    member_id, member_signup_token, access_token, redirect_url):
                    # Document requires a member to access (not "access_via_link")
                    # and we have a signup token -> redirect user to signup
                    return request.redirect(signup_url)
            return self._documents_render_public_view(document_sudo)
        elif request.env.user._is_portal():
            return self._documents_render_portal_view(document_sudo)
        else:  # assume internal user
            # Internal users use the /odoo/documents/<access_token> route
            return request.redirect(
                f'/odoo/documents/{quote(access_token, safe="")}?{keep_query("*")}',
                HTTPStatus.TEMPORARY_REDIRECT,
            )

    def _documents_render_public_view(self, document_sudo):
        target_sudo = document_sudo.shortcut_document_id
        if (
            target_sudo
            and target_sudo.access_via_link != 'none'
            and not target_sudo.is_access_via_link_hidden
        ):
            return request.redirect(
                f'/odoo/documents/{quote(target_sudo.access_token, safe="")}?{keep_query("*")}')
        if target_sudo or not document_sudo:
            return request.render(
                'documents.not_available', {'document': document_sudo}, status=404)
        if document_sudo.type == 'url':
            return request.redirect(
                document_sudo.url, code=HTTPStatus.TEMPORARY_REDIRECT, local=False)
        if document_sudo.type == 'binary' and document_sudo.attachment_id:
            return request.render('documents.share_file', {'document': document_sudo, 'quote': lambda v: quote(v, safe='')})
        if document_sudo.type == 'binary':
            return request.render('documents.document_request_page', {'document': document_sudo, 'quote': lambda v: quote(v, safe='')})
        if document_sudo.type == 'folder':
            sub_documents_sudo = ShareRoute._get_folder_children(document_sudo)
            return request.render('documents.public_folder_page', {
                'folder': document_sudo,
                'documents': sub_documents_sudo,
                'subfolders': {
                    sub_folder_sudo.id: ShareRoute._get_folder_children(sub_folder_sudo)
                    for sub_folder_sudo in sub_documents_sudo
                    if sub_folder_sudo.type == 'folder'
                },
                'quote': lambda v: quote(v, safe=''),
            })
        else:
            e = f"unknown document type {document_sudo.type}"
            raise NotImplementedError(e)

    def _documents_render_portal_view(self, document):
        """ Render the portal version (stripped version of the backend Documents app). """
        # We build the session information necessary for the web client to load
        session_info = request.env['ir.http'].session_info()
        mods = conf.server_wide_modules or []
        lang = request.env.context.get('lang')
        cache_hashes = {
            "translations": request.env['ir.http'].get_web_translations_hash(mods, lang),
        }

        session_info.update(
            cache_hashes=cache_hashes,
            user_companies={
                'current_company': request.env.company.id,
                'allowed_companies': {
                    request.env.company.id: {
                        'id': request.env.company.id,
                        'name': request.env.company.name,
                    },
                },
            },
            documents_init=self._documents_get_init_data(document, request.env.user),
        )

        return request.render(
            'documents.document_portal_view',
            {'session_info': session_info},
        )

    @classmethod
    def _documents_get_init_data(cls, document, user):
        """ Get initialization data to restore the interface on the selected document. """
        if not document or not user:
            return {}

        document.ensure_one()
        documents_init = {}

        # If the document is archived, we open the TRASH
        if not document.active:
            documents_init['folder_id'] = 'TRASH'
            documents_init['document_id'] = document.id
        # Shortcuts to archived folders behave like binary documents because these folders cannot be browsed.
        elif document.type != 'folder' or document.shortcut_document_id and not document.shortcut_document_id.active:
            parent = document.folder_id
            shared_root = False if user.share else "SHARED"  # Portal don't have 'Shared with me'
            # If the user does not have access to the parent folder, we open it in the "SHARED" folder.
            if parent:
                documents_init['folder_id'] = parent.id if parent.user_permission in {'view', 'edit'} else shared_root
            else:
                documents_init['folder_id'] = (
                    "MY" if document.owner_id == user
                    else "COMPANY" if not user.share and document.owner_id == document.env.ref('base.user_root')
                    else shared_root
                )
            documents_init['document_id'] = document.id
            target = document.shortcut_document_id or document
            if document.type == 'binary' and target.attachment_id:
                documents_init['open_preview'] = True
        else:
            documents_init['folder_id'] = document.id

        return documents_init

    @http.route('/documents/avatar/<access_token>',
                type='http', auth='public', readonly=True)
    def documents_avatar(self, access_token):
        """Show the avatar of the document's owner, or the avatar placeholder.

        :param access_token: the access token to the document record
        """
        partner_sudo = self._from_access_token(access_token, skip_log=True).owner_id.partner_id
        return request.env['ir.binary']._get_image_stream_from(
            partner_sudo, 'avatar_128', placeholder=partner_sudo._avatar_get_placeholder_path()
        ).get_response(as_attachment=False)

    @http.route('/documents/content/<access_token>',
                type='http', auth='public', readonly=True)
    def documents_content(self, access_token, download=True):
        """Serve the file of the document.

        :param access_token: the access token to the document record
        :param download: whether to download the document on the user's
            file system or to preview the document within the browser
        """
        document_sudo = self._from_access_token(access_token, skip_log=True)
        if not document_sudo:
            Redirect = request.env['documents.redirect'].sudo()
            if document_sudo := Redirect._get_redirection(access_token):
                return request.redirect(
                    f'/odoo/documents/{quote(document_sudo.access_token, safe="")}',
                    HTTPStatus.MOVED_PERMANENTLY,
                )
            raise request.not_found()
        if document_sudo.type == 'url':
            return request.redirect(
                document_sudo.url, code=HTTPStatus.TEMPORARY_REDIRECT, local=False)
        if document_sudo.type == 'folder':
            return self._make_zip(
                f'{document_sudo.name}.zip',
                self._get_folder_children(document_sudo),
            )
        if document_sudo.type == 'binary':
            if not document_sudo.attachment_id:
                raise request.not_found()
            with replace_exceptions(ValueError, by=BadRequest):
                download = str2bool(download)
            with replace_exceptions(ValueError, MissingError, by=request.not_found()):
                stream = self._documents_content_stream(document_sudo)
            return stream.get_response(as_attachment=download)
        e = f"unknown document type {document_sudo.type!r}"
        raise NotImplementedError(e)

    def _documents_content_stream(self, document_sudo):
        return request.env['ir.binary']._get_stream_from(document_sudo)

    @http.route('/documents/redirect/<access_token>', type='http', auth='public', readonly=True)
    def documents_redirect(self, access_token):
        return request.redirect(f'/odoo/documents/{quote(access_token, safe="")}', HTTPStatus.MOVED_PERMANENTLY)

    @http.route('/documents/touch/<access_token>', type='json', auth='user')
    def documents_touch(self, access_token):
        doc = self._from_access_token(access_token)
        if doc.env.context.get('document_newly_accessible'):
            return {'reload': True}
        return {}

    @http.route(['/documents/thumbnail/<access_token>',
                 '/documents/thumbnail/<access_token>/<int:width>x<int:height>'],
                type='http', auth='public', readonly=True)
    def documents_thumbnail(self, access_token, width='0', height='0', unique=''):
        """Show the thumbnail of the document, or a placeholder.

        :param access_token: the access token to the document record
        :param width: resize the thumbnail to this maximum width
        :param height: resize the thumbnail to this maximum height
        :param unique: force storing the file in the browser cache, best
            used with the checksum of the attachment
        """
        with replace_exceptions(ValueError, by=BadRequest):
            width = int(width)
            height = int(height)
        send_file_kwargs = {}
        if unique:
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
        document_sudo = self._from_access_token(access_token, skip_log=True)
        return request.env['ir.binary']._get_image_stream_from(
            document_sudo, 'thumbnail', width=width, height=height
        ).get_response(as_attachment=False, **send_file_kwargs)

    @http.route(['/documents/document/<int:document_id>/update_thumbnail'], type='json', auth='user')
    def documents_update_thumbnail(self, document_id, thumbnail):
        """Update the thumbnail of the document (after it has been generated by the browser).

        We update the thumbnail in SUDO, after checking the read access, so it will work
        if the user that generates the thumbnail is not the user who uploaded the document.
        """
        document = request.env['documents.document'].browse(document_id)
        document.check_access('read')
        if document.thumbnail_status != 'client_generated':
            return
        document.sudo().write({
            'thumbnail': thumbnail,
            'thumbnail_status': 'present' if thumbnail else 'error',
        })

    @http.route(['/documents/zip'], type='http', auth='user')
    def documents_zip(self, file_ids, zip_name, **kw):
        """Select many files / folders in the interface and click on download.

        :param file_ids: if of the files to zip.
        :param zip_name: name of the zip file.
        """
        ids_list = [int(x) for x in file_ids.split(',')]
        documents = request.env['documents.document'].browse(ids_list)
        documents.check_access('read')
        return self._make_zip(zip_name, documents)

    @http.route([
        '/document/download/all/<int:share_id>/<access_token>',
        '/document/download/all/<access_token>'], type='http', auth='public')
    def documents_download_all_legacy(self, access_token=None, share_id=None):
        logger.warning("Deprecated since Odoo 18. Please access /documents/content/<access_token> instead.")
        return request.redirect(f'/documents/content/{quote(access_token or "", safe="")}', HTTPStatus.MOVED_PERMANENTLY)

    @http.route([
        '/document/share/<int:share_id>/<token>',
        '/document/share/<token>'], type='http', auth='public')
    def share_portal(self, share_id=None, token=None):
        logger.warning("Deprecated since Odoo 18. Please access /odoo/documents/<access_token> instead.")
        return request.redirect(f'/odoo/documents/{quote(token or "", safe="")}', code=HTTPStatus.MOVED_PERMANENTLY)

    @http.route(['/documents/upload/', '/documents/upload/<access_token>'],
                type='http', auth='public', methods=['POST'],
                max_content_length=_max_content_length)
    def documents_upload(
        self,
        ufile,
        access_token='',
        owner_id='',
        partner_id='',
        res_id='',
        res_model='',
        allowed_company_ids='',
    ):
        """
        Replace an existing document or create new ones.

        :param ufile: a list of multipart/form-data files.
        :param access_token: the access token to a folder in which to
            create new documents, or the access token to an existing
            document where to upload/replace its attachment.
            A falsy value means no folder_id and is allowed for
            internal users to upload at the root of "My Drive".
        :param owner_id, partner_id, res_id, res_model: field values
            when creating new documents, for internal users only
        """
        if allowed_company_ids:
            request.update_context(allowed_company_ids=json.loads(allowed_company_ids))
        is_internal_user = request.env.user._is_internal()
        if is_internal_user and not access_token:
            document_sudo = request.env['documents.document'].sudo()
        else:
            document_sudo = self._from_access_token(access_token)
            if (
                not document_sudo
                or (document_sudo.user_permission != 'edit'
                    and document_sudo.access_via_link != 'edit')
                or document_sudo.type not in ('binary', 'folder')
            ):
                raise request.not_found()

        files = request.httprequest.files.getlist('ufile')
        if not files:
            raise BadRequest("missing files")
        if len(files) > 1 and document_sudo.type not in (False, 'folder'):
            raise BadRequest("cannot save multiple files inside a single document")

        if is_internal_user:
            with replace_exceptions(ValueError, by=BadRequest):
                owner_id = int(owner_id) if owner_id else request.env.user.id
                partner_id = int(partner_id) if partner_id else False
                res_model = res_model or 'documents.document'
                res_id = int(res_id) if res_id else False
        elif owner_id or partner_id or res_id or res_model:
            raise Forbidden("only internal users can provide field values")
        else:
            owner_id = document_sudo.owner_id.id if request.env.user.is_public else request.env.user.id
            partner_id = False
            res_model = 'documents.document'
            res_id = False  # replaced by the document's id

        document_ids = self._documents_upload(
            document_sudo, files, owner_id, partner_id, res_id, res_model)
        if len(document_ids) == 1:
            document_sudo = document_sudo.browse(document_ids)

        if request.env.user._is_public():
            return request.redirect(document_sudo.access_url)
        else:
            return request.make_json_response(document_ids)

    def _documents_upload(self,
            document_sudo, files, owner_id, partner_id, res_id, res_model):
        """ Replace an existing document or upload a new one. """
        is_internal_user = request.env.user._is_internal()

        document_ids = []
        AttachmentSudo = request.env['ir.attachment'] \
            .sudo(not is_internal_user) \
            .with_context(image_no_postprocess=True)

        if document_sudo.type == 'binary':
            attachment_sudo = AttachmentSudo._from_request_file(
                files[0], mimetype='TRUST' if is_internal_user else 'GUESS'
            )
            attachment_sudo.res_model = document_sudo.res_model
            attachment_sudo.res_id = document_sudo.res_id
            values = {'attachment_id': attachment_sudo.id}
            if not document_sudo.attachment_id:  # is a request
                if document_sudo.access_via_link == 'edit':
                    values['access_via_link'] = 'view'
            self._documents_upload_create_write(document_sudo, values)
            document_ids.append(document_sudo.id)
        else:
            folder_sudo = document_sudo
            for file in files:
                document_sudo = self._documents_upload_create_write(folder_sudo, {
                    'attachment_id': AttachmentSudo._from_request_file(
                        file, mimetype='TRUST' if is_internal_user else 'GUESS'
                    ).id,
                    'type': 'binary',
                    'access_via_link': 'none' if folder_sudo.access_via_link in (False, 'none') else 'view',
                    'folder_id': folder_sudo.id,
                    'owner_id': owner_id,
                    'partner_id': partner_id,
                    'res_model': res_model,
                    'res_id': res_id,
                })
                document_ids.append(document_sudo.id)

            # Make sure uploader can access documents in "Company"
            document_sudo.filtered(
                lambda d: not d.folder_id and d.owner_id == request.env.ref('base.user_root')
            ).action_update_access_rights(partners={request.env.user.partner_id: ('edit', False)})

        return document_ids

    def _documents_upload_create_write(self, document_sudo, vals):
        """
        The actual function that either write vals on a binary document
        or create a new document with vals inside a folder document.
        """
        if document_sudo.type == 'binary':
            document_sudo.write(vals)
        else:
            vals.setdefault('folder_id', document_sudo.id)
            document_sudo = document_sudo.create(vals)
        if not document_sudo.res_model:
            document_sudo.res_model = 'documents.document'
        if (
            document_sudo.res_model == 'documents.document'
            and not document_sudo.res_id
        ):
            document_sudo.res_id = document_sudo.id
        if (any(field_name in vals for field_name in [
                'raw', 'datas', 'attachment_id'])):
            document_sudo.message_post(body=_(
                "Document uploaded by %(user)s",
                user=request.env.user.name
            ))

        return document_sudo

    @http.route('/documents/upload_traceback', type='http', methods=['POST'], auth='user')
    def documents_upload_traceback(self, ufile, max_content_length=1 << 20):  # 1MiB
        if not request.env.user._is_internal():
            raise Forbidden()

        folder_sudo = request.env.ref(
            'documents.document_support_folder',
            raise_if_not_found=False
        ).sudo()
        if not folder_sudo or not folder_sudo.active:
            raise request.not_found()

        files = request.httprequest.files.getlist('ufile')
        if not files:
            raise BadRequest("missing files")
        if len(files) > 1:
            raise BadRequest("This route only accepts one file at a time.")

        traceback_sudo = self._documents_upload_create_write(folder_sudo, {
            'attachment_id': request.env['ir.attachment']._from_request_file(
                files[0], mimetype='text/plain').id,
            'type': 'binary',
            'access_internal': 'none',
            'access_via_link': 'view',
            'folder_id': folder_sudo.id,
            'owner_id': request.env.ref('base.user_root').id,
        })

        return request.make_json_response([traceback_sudo.access_url])


class DocumentsAttachmentController(AttachmentController):

    @http.route()
    def mail_attachment_upload(self, *args, **kw):
        """ Override to prevent the creation of a document when uploading
            an attachment from an activity already linked to a document."""
        if kw.get('activity_id'):
            document = request.env['documents.document'].search([('request_activity_id', '=', int(kw['activity_id']))])
            if document:
                request.update_context(no_document=True)
        return super().mail_attachment_upload(*args, **kw)
