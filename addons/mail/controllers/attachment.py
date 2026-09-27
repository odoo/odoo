# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
import zipfile

from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType

from odoo import _, http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.http.stream import content_disposition, STATIC_CACHE_LONG
from odoo.tools import BinaryBytes, file_open, str2bool
from odoo.tools.mail import html_remove_links, html_sanitize
from odoo.tools.misc import replace_exceptions
from odoo.tools.pdf import DependencyError, PdfReadError, extract_page

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import Store, add_guest_to_context, mail_route

logger = logging.getLogger(__name__)

try:
    from markdown2 import markdown
except ImportError:
    markdown = None
    logger.warning("markdown2 is not installed, markdown will not be rendered")


class AttachmentController(ThreadController):
    TEXTUAL_THUMBNAIL_SIZE = 4096
    SUPPORTED_TEXT_MIMETYPES = (
        'application/javascript', 'application/json', 'application/xml',
        'text/css', 'text/csv', 'text/html', 'text/markdown', 'text/plain', 'text/xml',
    )

    def _make_zip(self, name, attachments):
        streams = (request.env['ir.binary']._get_stream_from(record, 'raw') for record in attachments)
        # TODO: zip on-the-fly while streaming instead of loading the
        #       entire zip in memory and sending it all at once.
        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as attachment_zip:
                for binary_stream in streams:
                    if not binary_stream:
                        continue
                    attachment_zip.writestr(
                        binary_stream.download_name,
                        binary_stream.read(),
                        compress_type=zipfile.ZIP_DEFLATED
                    )
        except zipfile.BadZipFile:
            logger.exception("BadZipfile exception")

        content = stream.getvalue()
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(name))
        ]
        return request.make_response(content, headers)

    @mail_route("/mail/attachment/upload", methods=["POST"], type="http", auth="public")
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        thread = self._get_thread_with_access_for_post(thread_model, thread_id, **kwargs)
        if not thread:
            raise NotFound()
        vals = {
            "name": ufile.filename,
            "raw": ufile.read(),
            "res_id": int(thread_id),
            "res_model": thread_model,
        }
        if company_id := thread._mail_get_companies()[thread.id]:
            vals["company_id"] = company_id.id
        elif cids := request.cookies.get("cids", False):
            active_company_ids = [int(cid) for cid in cids.split("-")]
            company_id = (
                request.env.user.company_id.id
                if request.env.user.company_id.id in active_company_ids
                else active_company_ids[0]
            )
            vals["company_id"] = company_id
        if is_pending and is_pending != "false":
            # Add this point, the message related to the uploaded file does
            # not exist yet, so we use those placeholder values instead.
            vals.update(
                {
                    "res_id": 0,
                    "res_model": "mail.compose.message",
                }
            )
        try:
            # sudo: ir.attachment - posting a new attachment on an accessible thread
            attachment = request.env["ir.attachment"].sudo().create(vals)
            attachment._post_add_create(**kwargs)
            store = Store().add(
                attachment,
                lambda res: (
                    res.from_method("_store_attachment_fields", chatter_fields=not request.env.user.share),
                    res.from_method("_store_ownership_fields"),
                ),
            )
            res = {"data": {"store_data": store, "attachment_id": attachment.id}}
        except AccessError:
            res = {"error": _("You are not allowed to upload an attachment here.")}
        return request.make_json_response(res)

    @mail_route("/mail/attachment/delete", methods=["POST"], type="jsonrpc", auth="public")
    def mail_attachment_delete(self, access_token_by_attachment_id, keep_on_messages=False):
        """ Delete the given attachments at once, so that removing several of
            them, such as the copies of a same file, takes a single query.

            :param dict access_token_by_attachment_id: ownership token of each
                attachment to delete, keyed by attachment id. A token may be
                None to rely on the access rights only.
            :param bool keep_on_messages: only unlink the attachments posted on
                a message from their thread, keeping them on that message. Set
                when deleting from the attachment list of a record, as trimming
                that list is not meant to edit the messages of the record.
            :return: the ids of the attachments that were kept on their message
        """
        access_token_by_attachment_id = {
            int(attachment_id): access_token
            for attachment_id, access_token in access_token_by_attachment_id.items()
        }
        attachments = request.env["ir.attachment"].browse(access_token_by_attachment_id.keys()).exists()
        is_allowed = len(attachments) == len(access_token_by_attachment_id) and (
            attachments._has_attachments_ownership(
                [access_token_by_attachment_id[attachment.id] for attachment in attachments]
            )
        )
        if not is_allowed:
            for attachment_id in access_token_by_attachment_id:
                request.env.user._bus_send("ir.attachment/delete", {"id": attachment_id})
            raise NotFound()
        messages = request.env["mail.message"].sudo().search([("attachment_ids", "in", attachments.ids)])
        attachments_by_message = {message: attachments & message.attachment_ids for message in messages}
        posted = attachments & messages.attachment_ids
        orphans = attachments - posted
        for message, message_attachments in attachments_by_message.items():
            if keep_on_messages:
                # sudo: ir.attachment: access is validated with _has_attachments_ownership
                message_attachments.sudo()._unlink_from_thread_and_notify(message)
                continue
            thread = request.env[message.model].browse(message.res_id)
            thread._message_update_content(message, body=message.body)  # marks the message edited
            # sudo: ir.attachment: access is validated with _has_attachments_ownership
            message_attachments.sudo()._delete_and_notify(message)
        # sudo: ir.attachment: access is validated with _has_attachments_ownership
        orphans.sudo()._delete_and_notify()
        return {"kept_attachment_ids": posted.ids if keep_on_messages else []}

    @mail_route(['/mail/attachment/zip'], methods=["POST"], type="http", auth="public")
    def mail_attachment_get_zip(self, file_ids, zip_name, **kw):
        """route to get the zip file of the attachments.
        :param file_ids: ids of the files to zip.
        :param zip_name: name of the zip file.
        """
        ids_list = list(map(int, file_ids.split(',')))
        attachments = request.env['ir.attachment'].browse(ids_list)
        return self._make_zip(zip_name, attachments)

    @http.route(
        "/mail/attachment/pdf_first_page/<int:attachment_id>",
        auth="public",
        methods=["GET"],
        readonly=True,
        type="http",
    )
    @add_guest_to_context
    def mail_attachment_pdf_first_page(self, attachment_id, access_token=None):
        """Returns the first page of a pdf."""
        attachment = request.env["ir.attachment"].browse(int(attachment_id)).exists()
        if not attachment or (
            not attachment.has_access("read")
            and not attachment._has_attachments_ownership([access_token])
        ):
            raise request.not_found()
        # sudo: ir.attachment: access check is done above, sudo necessary for guests
        return self._get_pdf_first_page_response(attachment.sudo())

    @mail_route(
        "/mail/attachment/update_thumbnail",
        auth="public",
        methods=["POST"],
        type="jsonrpc",
    )
    def mail_attachement_update_thumbnail(self, attachment_id, thumbnail=None, access_token=None):
        """Updates the thumbnail of an attachment."""
        attachment = request.env["ir.attachment"].browse(int(attachment_id)).exists()
        if not attachment or (
            not attachment.has_access("write")
            and not attachment._has_attachments_ownership([access_token])
        ):
            raise request.not_found()
        # sudo: ir.attachment: access check is done above, sudo necessary for guests
        attachment_sudo = attachment.sudo()
        if attachment_sudo.mimetype != "application/pdf" and not attachment_sudo.mimetype.startswith('video/'):
            raise UserError(request.env._("Only PDF and videos files can have thumbnail."))
        if thumbnail:
            thumbnail = BinaryBytes(base64.b64decode(thumbnail))
        else:
            with file_open("web/static/img/mimetypes/unknown.svg", "rb") as f:
                thumbnail = BinaryBytes(f.read())
        attachment_sudo.thumbnail = thumbnail
        Store(bus_channel=attachment_sudo).add(attachment_sudo, ["has_thumbnail"])

    def _get_pdf_first_page_response(self, attachment):
        try:
            page_stream = extract_page(attachment, 0)
        except (PdfReadError, DependencyError, UnicodeDecodeError) as e:
            raise UnsupportedMediaType() from e
        if not page_stream:
            raise UnsupportedMediaType()
        content = page_stream.getvalue()
        headers = [
            ("Content-Type", "attachment/pdf"),
            ("X-Content-Type-Options", "nosniff"),
            ("Content-Length", len(content)),
        ]
        if attachment.name:
            headers.append(("Content-Disposition", content_disposition(attachment.name)))
        return request.make_response(content, headers)

    @http.route(
        "/mail/attachment/render_text/<int:attachment_id>",
        type="http",
        auth="public",
        readonly=True,
    )
    def mail_attachment_render_text(self, attachment_id, access_token=None, head=False, unique=False, **kwargs):
        """Render the text content for preview and thumbnail.

        Render the document content / preview for:
        - Simple text
        - HTML
        - XML
        - JSON
        - Markdown

        :param int attachment_id: ID of the attachment
        :param str access_token: The access token to the record
        :param bool head: Show only the thumbnail (first 4kiB) of text-like documents.
            Note: HTML files are always streamed in full to prevent breaking their structural markup.
        :param str unique: Indicates if the response can be cached
        """
        with replace_exceptions(AccessError, MissingError, by=request.not_found()):
            attachment = request.env['ir.binary']._find_record(
                res_model='ir.attachment',
                res_id=int(attachment_id),
                access_token=access_token,
                field='raw',
            )
        return self._render_text_attachment(attachment, str2bool(head, False), unique)

    def _set_render_with_headers(self, response, unique):
        """Apply the security headers and cache policy shared by every rendered text preview"""
        response.headers['Content-Security-Policy'] = (
            "default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self'; sandbox;"
        )
        # Settings below are mirroring settings in stream.get_response()
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.cache_control.pop('public', '')
        response.cache_control.private = True
        if unique:
            response.cache_control['immutable'] = None
            response.cache_control.max_age = STATIC_CACHE_LONG
        return response

    def _render_text_attachment(self, attachment, head=False, unique=False):
        """Shared rendering engine for text attachments."""
        mimetype = attachment.mimetype
        if mimetype not in self.SUPPORTED_TEXT_MIMETYPES:
            raise BadRequest(f"bad document mimetype: expect a recognized text type, got {mimetype}")
        immutable = bool(unique) and unique == attachment.checksum
        if (mimetype == 'application/json' and not head) or mimetype == 'text/html':
            with replace_exceptions(ValueError, MissingError, by=request.not_found()):
                stream = request.env['ir.binary']._get_stream_from(attachment)
            stream.public = False
            return stream.get_response(
                as_attachment=False, immutable=immutable, content_security_policy="default-src 'none'; sandbox;"
            )
        with attachment.raw.open() as f:
            content = f.read(self.TEXTUAL_THUMBNAIL_SIZE) if head else f.read()
        text_content = content.decode(errors='replace')
        if mimetype == 'text/markdown' and markdown:
            rendered = markdown(
                text_content,
                safe_mode='escape',
                extras=['strike', 'fenced-code-blocks', 'tables', 'footnotes'],
            )
            response = request.render("mail.content_markdown", {
                'content': html_sanitize(
                    html_remove_links(rendered),
                    sanitize_attributes=True,
                    strip_style=True,
                    strip_classes=True,
                ),
            })
        else:
            response = request.render("mail.content_text", {
                'content': text_content,
            })
        return self._set_render_with_headers(response, immutable)
