# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import _
from odoo.http import route, request
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.exceptions import AccessError
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class LivechatAttachmentController(AttachmentController):
    @route()
    @add_guest_to_context
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        post_access = request.env[thread_model].sudo()._get_mail_message_access(int(thread_id), "create")
        thread = request.env[thread_model]._get_thread_with_access(int(thread_id), mode=post_access, **kwargs)
        if not thread:
            raise NotFound()
        if (
            thread_model == "discuss.channel"
            and thread.channel_type == "livechat"
            and not thread.livechat_active
            and not request.env.user._is_internal()
        ):
            raise AccessError(_("You are not allowed to upload attachments on this channel."))
        return super().mail_attachment_upload(ufile, thread_id, thread_model, is_pending, **kwargs)
