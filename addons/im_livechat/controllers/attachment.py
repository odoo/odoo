from odoo.http import route
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class LivechatThreadController(AttachmentController):
    @route("/mail/attachment/upload", cors="*", csrf=False)
    @add_guest_to_context
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        return super().mail_attachment_upload(ufile, thread_id, thread_model, is_pending, **kwargs)

    @route("/mail/attachment/delete", cors="*")
    @add_guest_to_context
    def mail_attachment_delete(self, attachment_id, access_token=None):
        return super().mail_attachment_delete(attachment_id, access_token)
