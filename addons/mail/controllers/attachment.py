# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq


class AttachmentController(http.Controller):
    @http.route("/mail/attachment/upload", methods=["POST"], type="http", auth="public")
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        env = request.env["ir.attachment"]._get_upload_env(request, thread_model, thread_id)
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
            attachment._post_add_create()
            attachmentData = {
                "filename": ufile.filename,
                "id": attachment.id,
                "mimetype": attachment.mimetype,
                "name": attachment.name,
                "size": attachment.file_size,
            }
            if attachment.access_token:
                attachmentData["accessToken"] = attachment.access_token
        except AccessError:
            attachmentData = {"error": _("You are not allowed to upload an attachment here.")}
        return request.make_json_response(attachmentData)

    @http.route("/mail/attachment/delete", methods=["POST"], type="json", auth="public")
    def mail_attachment_delete(self, attachment_id, access_token=None):
        attachment_sudo = request.env["ir.attachment"].browse(int(attachment_id)).sudo().exists()
        guest = request.env["mail.guest"]._get_guest_from_request(request)
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
