from odoo.http import route
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class LivechatAttachmentController(AttachmentController):
    @route("/im_livechat/cors/attachment/upload", auth="public", cors="*", csrf=False)
    def im_livechat_attachment_upload(self, guest_token, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        force_guest_env(guest_token)
        return self.mail_attachment_upload(ufile, thread_id, thread_model, is_pending, **kwargs)

    @route("/im_livechat/cors/attachment/delete", methods=["POST"], type="json", auth="public", cors="*")
    def im_livechat_attachment_delete(self, guest_token, attachment_id, access_token=None):
        force_guest_env(guest_token)
        return self.mail_attachment_delete(attachment_id, access_token)
