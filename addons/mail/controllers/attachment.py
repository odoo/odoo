# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging
import zipfile

from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request, content_disposition

from odoo.tools import consteq
from ..models.discuss.mail_guest import add_guest_to_context

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
        env = request.env["ir.attachment"]._get_upload_env(thread_model, thread_id)
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
        if env.user.share:
            # Only generate the access token if absolutely necessary (= not for internal user).
            vals["access_token"] = env["ir.attachment"]._generate_access_token()
        try:
            attachment = env["ir.attachment"].create(vals)
            attachment._post_add_create(**kwargs)
            attachmentData = attachment._attachment_format()[0]
            if attachment.access_token:
                attachmentData["accessToken"] = attachment.access_token
        except AccessError:
            attachmentData = {"error": _("You are not allowed to upload an attachment here.")}
        return request.make_json_response(attachmentData)

    @http.route("/mail/attachment/delete", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_attachment_delete(self, attachment_id, access_token=None):
        attachment_sudo = request.env["ir.attachment"].browse(int(attachment_id)).sudo().exists()
        guest = request.env["mail.guest"]._get_guest_from_context()
        message_sudo = guest.env["mail.message"].sudo().search([("attachment_ids", "in", attachment_sudo.ids)], limit=1)
        if not attachment_sudo:
            target = request.env.user.partner_id
            request.env["bus.bus"]._sendone(target, "ir.attachment/delete", {"id": attachment_id})
            return
        if not request.env.user.share:
            # Check through standard access rights/rules for internal users.
            attachment_sudo.sudo(False)._delete_and_notify(message_sudo)
            return
        # For non-internal users 2 cases are supported:
        #   - Either the attachment is linked to a message: verify the request is made by the author of the message (portal user or guest).
        #   - Either a valid access token is given: also verify the message is pending (because unfortunately in portal a token is also provided to guest for viewing others' attachments).
        if message_sudo:
            if not message_sudo.is_current_user_or_guest_author:
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
        attachment_sudo._delete_and_notify(message_sudo)

    @http.route(['/mail/attachment/zip'], methods=["POST"], type="http", auth="public")
    def mail_attachment_get_zip(self, file_ids, zip_name, **kw):
        """route to get the zip file of the attachments.
        :param file_ids: ids of the files to zip.
        :param zip_name: name of the zip file.
        """
        ids_list = list(map(int, file_ids.split(',')))
        attachments = request.env['ir.attachment'].browse(ids_list)
        return self._make_zip(zip_name, attachments)
