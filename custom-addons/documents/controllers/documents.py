# -*- coding: utf-8 -*-

import base64
import io
import json
import logging
import zipfile
from contextlib import ExitStack

from markupsafe import Markup
from werkzeug.exceptions import Forbidden

from odoo import Command, http
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.exceptions import AccessError
from odoo.http import request, content_disposition
from odoo.tools.translate import _

logger = logging.getLogger(__name__)


class ShareRoute(http.Controller):

    # util methods #################################################################################

    def _get_file_response(self, res_id, share_id=None, share_token=None, field='raw', as_attachment=None):
        """ returns the http response to download one file. """
        record = request.env['documents.document'].browse(int(res_id))

        if share_id:
            share = request.env['documents.share'].sudo().browse(int(share_id))
            record = share._get_documents_and_check_access(share_token, [int(res_id)], operation='read')
        if not record or not record.exists():
            raise request.not_found()

        if record.type == 'url':
            if isinstance(record.url, str):
                url = record.url if record.url.startswith(('http://', 'https://', 'ftp://')) else 'http://' + record.url
            else:
                url = record.url
            return request.redirect(url, code=307, local=False)

        filename = (record.name if not record.file_extension or record.name.endswith(f'.{record.file_extension}')
                    else f'{record.name}.{record.file_extension}')
        return request.env['ir.binary']._get_stream_from(record, field, filename=filename).get_response(as_attachment)

    @classmethod
    def _get_downloadable_documents(cls, documents):
        """Only files are downloadable."""
        return documents.filtered(lambda d: d.type == "binary")

    @classmethod
    def _make_zip(cls, name, documents):
        streams = (
            request.env['ir.binary']._get_stream_from(document, 'raw')
            for document in cls._get_downloadable_documents(documents)
        )
        return cls._generate_zip(name, streams)

    @classmethod
    def _generate_zip(cls, name, file_streams):
        """returns zip files for the Document Inspector and the portal.

        :param name: the name to give to the zip file.
        :param file_streams: binary file streams to be zipped.
        :return: a http response to download a zip file.
        """
        # TODO: zip on-the-fly while streaming instead of loading the
        #       entire zip in memory and sending it all at once.

        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                for binary_stream in file_streams:
                    if not binary_stream:
                        continue
                    doc_zip.writestr(
                        binary_stream.download_name,
                        binary_stream.read(),  # Cf Todo: this is bad
                        compress_type=zipfile.ZIP_DEFLATED
                    )
        except zipfile.BadZipfile:
            logger.exception("BadZipfile exception")

        content = stream.getvalue()  # Cf Todo: this is bad
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(name))
        ]
        return request.make_response(content, headers)

    # Download & upload routes #####################################################################

    @http.route('/documents/upload_attachment', type='http', methods=['POST'], auth="user")
    def upload_document(self, folder_id, ufile, tag_ids, document_id=False, partner_id=False, owner_id=False, res_id=False, res_model=False):
        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        tag_ids = tag_ids.split(',') if tag_ids else []
        if document_id:
            document = request.env['documents.document'].browse(int(document_id))
            ufile = files[0]
            try:
                data = base64.encodebytes(ufile.read())
                mimetype = ufile.content_type
                document.write({
                    'name': ufile.filename,
                    'datas': data,
                    'mimetype': mimetype,
                })
            except Exception as e:
                logger.exception("Fail to upload document %s" % ufile.filename)
                result = {'error': str(e)}
        else:
            vals_list = []
            for ufile in files:
                try:
                    mimetype = ufile.content_type
                    datas = base64.encodebytes(ufile.read())
                    vals = {
                        'name': ufile.filename,
                        'mimetype': mimetype,
                        'datas': datas,
                        'folder_id': int(folder_id),
                        'tag_ids': tag_ids,
                        'partner_id': int(partner_id)
                    }
                    if owner_id:
                        vals['owner_id'] = int(owner_id)
                    if res_id and res_model:
                        vals['res_id'] = res_id
                        vals['res_model'] = res_model
                    vals_list.append(vals)
                except Exception as e:
                    logger.exception("Fail to upload document %s" % ufile.filename)
                    result = {'error': str(e)}
            cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
            allowed_company_ids = [int(cid) for cid in cids.split(',')]
            documents = request.env['documents.document'].with_context(allowed_company_ids=allowed_company_ids).create(vals_list)
            result['ids'] = documents.ids

        return json.dumps(result)

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

    @http.route(['/documents/content/<int:id>'], type='http', auth='user')
    def documents_content(self, id):
        return self._get_file_response(id)

    @http.route(['/documents/pdf_content/<int:document_id>'], type='http', auth='user')
    def documents_pdf_content(self, document_id):
        """
        This route is used to fetch the content of a pdf document to make it's thumbnail.
        404 not found is returned if the user does not hadocument_idve the rights to write on the document.
        """
        record = request.env['documents.document'].browse(int(document_id))
        try:
            # We have to check that we can actually read the attachment as well.
            # Since we could have a document with an attachment linked to another record to which
            # we don't have access to.
            if record.attachment_id:
                record.attachment_id.check('read')
            record.check_access_rule('write')
        except AccessError:
            raise Forbidden()
        return self._get_file_response(document_id)

    @http.route(['/documents/image/<int:res_id>',
                 '/documents/image/<int:res_id>/<int:width>x<int:height>',
                 ], type='http', auth="public")
    def content_image(self, res_id=None, field='datas', share_id=None, width=0, height=0, crop=False, share_token=None, **kwargs):
        record = request.env['documents.document'].browse(int(res_id))
        if share_id:
            share = request.env['documents.share'].sudo().browse(int(share_id))
            record = share._get_documents_and_check_access(share_token, [int(res_id)], operation='read')
        if not record or not record.exists():
            raise request.not_found()

        return request.env['ir.binary']._get_image_stream_from(
            record, field, width=int(width), height=int(height), crop=crop
        ).get_response()

    @http.route(['/document/zip'], type='http', auth='user')
    def get_zip(self, file_ids, zip_name, **kw):
        """route to get the zip file of the selection in the document's Kanban view (Document inspector).
        :param file_ids: if of the files to zip.
        :param zip_name: name of the zip file.
        """
        ids_list = [int(x) for x in file_ids.split(',')]
        documents = request.env['documents.document'].browse(ids_list)
        documents.check_access_rights('read')
        response = self._make_zip(zip_name, documents)
        return response

    @http.route(["/document/download/all/<int:share_id>/<access_token>"], type='http', auth='public')
    def share_download_all(self, access_token=None, share_id=None):
        """
        :param share_id: id of the share, the name of the share will be the name of the zip file share.
        :param access_token: share access token
        :returns the http response for a zip file if the token and the ID are valid.
        """
        env = request.env
        try:
            share = env['documents.share'].sudo().browse(share_id)
            documents = share._get_documents_and_check_access(access_token, operation='read')
            if not documents:
                raise request.not_found()
            streams = (
                self._get_share_zip_data_stream(share, document)
                for document in documents
            )
            return self._generate_zip((share.name or 'unnamed-link') + '.zip', streams)
        except Exception:
            logger.exception("Failed to zip share link id: %s" % share_id)
        raise request.not_found()

    @classmethod
    def _get_share_zip_data_stream(cls, share, document):
        if document == cls._get_downloadable_documents(document):
            return request.env['ir.binary']._get_stream_from(document, 'raw')
        return False

    @http.route([
        "/document/avatar/<int:share_id>/<access_token>",
        "/document/avatar/<int:share_id>/<access_token>/<document_id>",
    ], type='http', auth='public')
    def get_avatar(self, access_token=None, share_id=None, document_id=None):
        """
        :param share_id: id of the share.
        :param access_token: share access token
        :returns the picture of the share author for the front-end view.
        """
        try:
            env = request.env
            share = env['documents.share'].sudo().browse(share_id)
            if share._get_documents_and_check_access(access_token, document_ids=[], operation='read') is not False:
                if document_id:
                    user = env['documents.document'].sudo().browse(int(document_id)).owner_id
                    if not user:
                        return env['ir.binary']._placeholder()
                else:
                    user = share.create_uid
                return request.env['ir.binary']._get_stream_from(user, 'avatar_128').get_response()
            else:
                return request.not_found()
        except Exception:
            logger.exception("Failed to download portrait")
        return request.not_found()

    @http.route(["/document/thumbnail/<int:share_id>/<access_token>/<int:id>"],
                type='http', auth='public')
    def get_thumbnail(self, id=None, access_token=None, share_id=None):
        """
        :param id:  id of the document
        :param access_token: token of the share link
        :param share_id: id of the share link
        :return: the thumbnail of the document for the portal view.
        """
        try:
            thumbnail = self._get_file_response(id, share_id=share_id, share_token=access_token, field='thumbnail')
            return thumbnail
        except Exception:
            logger.exception("Failed to download thumbnail id: %s" % id)
        return request.not_found()

    # single file download route.
    @http.route(["/document/download/<int:share_id>/<access_token>/<int:document_id>"],
                type='http', auth='public')
    def download_one(self, document_id=None, access_token=None, share_id=None, preview=None, **kwargs):
        """
        used to download a single file from the portal multi-file page.

        :param id: id of the file
        :param access_token:  token of the share link
        :param share_id: id of the share link
        :return: a portal page to preview and download a single file.
        """
        try:
            document = self._get_file_response(document_id, share_id=share_id, share_token=access_token, field='raw', as_attachment=not bool(preview))
            return document or request.not_found()
        except Exception:
            logger.exception("Failed to download document %s" % id)

        return request.not_found()

    def _create_uploaded_documents(self, files, share, folder, documents_values=None):
        documents_values = {
            'tag_ids': [Command.set(share.tag_ids.ids)],
            'partner_id': share.partner_id.id,
            'owner_id': share.owner_id.user_ids[0].id if share.owner_id.user_ids else share.create_uid.id,
            'folder_id': folder.id,
            **(documents_values or {}),
        }
        documents = request.env['documents.document']
        documents.with_user(share.create_uid).check_access_rights('create')
        max_upload_size = documents.get_document_max_upload_limit()
        for file in files:
            data = file.read()
            if max_upload_size and len(data) > max_upload_size:
                # TODO return error when converted to json
                logger.exception("File is too large.")
                raise Exception
            document_dict = {
                'mimetype': file.content_type,
                'name': file.filename,
                'datas': base64.b64encode(data),
                **documents_values,
            }
            documents |= documents.sudo().create(document_dict).sudo(False)
        documents.with_user(share.create_uid).check_access_rule('create')
        return documents

    # Upload file(s) route.
    @http.route(["/document/upload/<int:share_id>/<token>/",
                 "/document/upload/<int:share_id>/<token>/<int:document_id>"],
                type='http', auth='public', methods=['POST'], csrf=False)
    def upload_attachment(self, share_id, token, document_id=None, **kwargs):
        """
        Allows public upload if provided with the right token and share_Link.

        :param share_id: id of the share.
        :param token: share access token.
        :param document_id: id of a document request to directly upload its content
        :return if files are uploaded, recalls the share portal with the updated content.
        """
        share = http.request.env['documents.share'].sudo().browse(share_id)
        if not share.can_upload or (not document_id and share.action != 'downloadupload'):
            return http.request.not_found()

        available_documents = share._get_documents_and_check_access(
            token, [document_id] if document_id else [], operation='write')
        folder = share.folder_id
        folder_id = folder.id or False
        button_text = share.name or _('Share link')
        chatter_message = Markup("""<b>%s</b> %s <br/>
                               <b>%s</b> %s <br/>
                               <a class="btn btn-primary" href="/web#id=%s&model=documents.share&view_type=form" target="_blank">
                                  <b>%s</b>
                               </a>
                             """) % (
                _("File uploaded by:"),
                http.request.env.user.name,
                _("Link created by:"),
                share.create_uid.name,
                share_id,
                button_text,
            )
        Documents = request.env['documents.document']
        if document_id and available_documents:
            if available_documents.type != 'empty':
                return http.request.not_found()
            try:
                max_upload_size = Documents.get_document_max_upload_limit()
                file = request.httprequest.files.getlist('requestFile')[0]
                data = file.read()
                if max_upload_size and (len(data) > int(max_upload_size)):
                    # TODO return error when converted to json
                    return logger.exception("File is too Large.")
                mimetype = file.content_type
                write_vals = {
                    'mimetype': mimetype,
                    'name': file.filename,
                    'type': 'binary',
                    'datas': base64.b64encode(data),
                }
            except Exception:
                logger.exception("Failed to read uploaded file")
            else:
                available_documents.write(write_vals)
                available_documents.message_post(body=chatter_message)
        elif not document_id and available_documents is not False:
            try:
                documents = self._create_uploaded_documents(request.httprequest.files.getlist('files'), share, folder)
            except Exception:
                logger.exception("Failed to upload document")
            else:
                for document in documents:
                    document.sudo().message_post(body=chatter_message)
                if share.activity_option:
                    documents.sudo().documents_set_activity(settings_record=share)
        else:
            return http.request.not_found()
        return Markup("""<script type='text/javascript'>
                    window.open("/document/share/%s/%s", "_self");
                </script>""") % (share_id, token)

    # Frontend portals #############################################################################

    # share portals route.
    @http.route(['/document/share/<int:share_id>/<token>'], type='http', auth='public')
    def share_portal(self, share_id=None, token=None):
        """
        Leads to a public portal displaying downloadable files for anyone with the token.

        :param share_id: id of the share link
        :param token: share access token
        """
        try:
            share = http.request.env['documents.share'].sudo().browse(share_id)
            available_documents = share._get_documents_and_check_access(token, operation='read')
            if available_documents is False:
                if share._check_token(token):
                    options = {
                        'expiration_date': share.date_deadline,
                        'author': share.create_uid.name,
                    }
                    return request.render('documents.not_available', options)
                else:
                    return request.not_found()

            shareable_documents = available_documents.filtered(lambda r: r.type != 'url')
            options = {
                'name': share.name,
                'base_url': share.get_base_url(),
                'token': str(token),
                'upload': share.action == 'downloadupload',
                'share_id': str(share.id),
                'author': share.create_uid.name,
                'date_deadline': share.date_deadline,
                'document_ids': shareable_documents,
            }
            if len(shareable_documents) == 1 and shareable_documents.type == 'empty':
                return request.render("documents.document_request_page", options)
            elif share.type == 'domain':
                options.update(all_button='binary' in [document.type for document in shareable_documents],
                               request_upload=share.action == 'downloadupload')
                return request.render('documents.share_workspace_page', options)

            total_size = sum(document.file_size for document in shareable_documents)
            options.update(file_size=total_size, is_files_shared=True)
            return request.render("documents.share_files_page", options)
        except Exception:
            logger.exception("Failed to generate the multi file share portal")
        return request.not_found()


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
