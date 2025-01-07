# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging
import zipfile

from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.exceptions import AccessError
from odoo.http import request, content_disposition

from odoo.tools import consteq
from ..models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store

logger = logging.getLogger(__name__)


class AttachmentController(http.Controller):
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
        thread = ThreadController._get_thread_with_access(thread_model, thread_id, mode=request.env[thread_model]._mail_post_access, **kwargs)
        if not thread:
            raise NotFound()
        if thread_model == "discuss.channel" and not thread.allow_public_upload and not request.env.user._is_internal():
            raise AccessError(_("You are not allowed to upload attachments on this channel."))
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
        if request.env.user.share:
            # Only generate the access token if absolutely necessary (= not for internal user).
            vals["access_token"] = request.env["ir.attachment"]._generate_access_token()
        try:
            # sudo: ir.attachment - posting a new attachment on an accessible thread
            attachment = request.env["ir.attachment"].sudo().create(vals)
            attachment._post_add_create(**kwargs)
            res = {"data": Store(attachment, extra_fields="access_token").get_result()}
        except AccessError:
            res = {"error": _("You are not allowed to upload an attachment here.")}
        return request.make_json_response(res)

    @http.route("/mail/attachment/delete", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_attachment_delete(self, attachment_id, access_token=None, **kwargs):
        attachment = request.env["ir.attachment"].browse(int(attachment_id)).exists()
        if not attachment:
            request.env.user._bus_send("ir.attachment/delete", {"id": attachment_id})
            return
        attachment_message = request.env["mail.message"].sudo().search(
            [("attachment_ids", "in", attachment.ids)], limit=1)
        message = ThreadController._get_message_with_access(attachment_message.id, mode="create", **kwargs)
        if not request.env.user.share:
            # Check through standard access rights/rules for internal users.
            attachment._delete_and_notify(message)
            return
        # For non-internal users 2 cases are supported:
        #   - Either the attachment is linked to a message: verify the request is made by the author of the message (portal user or guest).
        #   - Either a valid access token is given: also verify the message is pending (because unfortunately in portal a token is also provided to guest for viewing others' attachments).
        # sudo: ir.attachment: access is validated below with membership of message or access token
        attachment_sudo = attachment.sudo()
        if message:
            if not ThreadController._can_delete_attachment(message, **kwargs):
                raise NotFound()
        else:
            if (
                not access_token
                or not attachment_sudo.access_token
                or not consteq(access_token, attachment_sudo.access_token)
            ):
                raise NotFound()
            if attachment_sudo.res_model != "mail.compose.message" or attachment_sudo.res_id != 0:
                raise NotFound()
        attachment_sudo._delete_and_notify(message)

    @http.route(['/mail/attachment/zip'], methods=["POST"], type="http", auth="public")
    def mail_attachment_get_zip(self, file_ids, zip_name, **kw):
        """route to get the zip file of the attachments.
        :param file_ids: ids of the files to zip.
        :param zip_name: name of the zip file.
        """
        ids_list = list(map(int, file_ids.split(',')))
        attachments = request.env['ir.attachment'].browse(ids_list)
        return self._make_zip(zip_name, attachments)
