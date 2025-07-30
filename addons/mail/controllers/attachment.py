# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging
import zipfile

from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.exceptions import AccessError
from odoo.http import request, content_disposition
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store

logger = logging.getLogger(__name__)


class AttachmentController(ThreadController):
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

    @http.route("/mail/attachment/upload", methods=["POST"], type="http", auth="public")
    @add_guest_to_context
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
            res = {
                "data": Store().add(
                    attachment,
                    extra_fields=request.env["ir.attachment"]._get_store_ownership_fields(),
                ).get_result()
            }
        except AccessError:
            res = {"error": _("You are not allowed to upload an attachment here.")}
        return request.make_json_response(res)

    @http.route("/mail/attachment/delete", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_attachment_delete(self, attachment_id, access_token=None):
        attachment = request.env["ir.attachment"].browse(int(attachment_id)).exists()
        if not attachment or not attachment._has_attachments_ownership([access_token]):
            request.env.user._bus_send("ir.attachment/delete", {"id": attachment_id})
            raise NotFound()
        message = request.env["mail.message"].sudo().search(
            [("attachment_ids", "in", attachment.ids)], limit=1)
        # sudo: ir.attachment: access is validated with _has_attachments_ownership
        attachment.sudo()._delete_and_notify(message)

    @http.route(['/mail/attachment/zip'], methods=["POST"], type="http", auth="public")
    def mail_attachment_get_zip(self, file_ids, zip_name, **kw):
        """route to get the zip file of the attachments.
        :param file_ids: ids of the files to zip.
        :param zip_name: name of the zip file.
        """
        ids_list = list(map(int, file_ids.split(',')))
        attachments = request.env['ir.attachment'].browse(ids_list)
        return self._make_zip(zip_name, attachments)
