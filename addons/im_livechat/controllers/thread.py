# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context

class LivechatThreadController(ThreadController):
    @route("/mail/message/post", cors="*")
    @add_guest_to_context
    def mail_message_post(self, thread_model, thread_id, post_data, context=None):
        return super().mail_message_post(thread_model, thread_id, post_data, context)

    @route("/mail/message/update_content", cors="*")
    @add_guest_to_context
    def mail_message_update_content(self, message_id, body, attachment_ids, attachment_tokens=None, partner_ids=None):
        return super().mail_message_update_content(message_id, body, attachment_ids, attachment_tokens, partner_ids)
