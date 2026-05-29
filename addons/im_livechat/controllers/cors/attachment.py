from odoo.http import route

from odoo.addons.mail.controllers.attachment import AttachmentController


class LivechatAttachmentController(AttachmentController):
    @route("/im_livechat/cors/attachment/upload", auth="force_guest", cors="*", csrf=False)
    def im_livechat_attachment_upload(
        self,
        guest_token,
        ufile,
        thread_id,
        thread_model,
        is_pending=False,
        **kwargs,
    ):
        return self.mail_attachment_upload(ufile, thread_id, thread_model, is_pending, **kwargs)

    @route(
        "/im_livechat/cors/attachment/delete",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def im_livechat_attachment_delete(self, guest_token, attachment_id, access_token=None):
        return self.mail_attachment_delete(attachment_id, access_token)
