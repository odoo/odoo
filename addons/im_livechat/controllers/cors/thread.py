# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.mail.controllers.thread import ThreadController


class LivechatThreadController(ThreadController):
    @route(
        "/im_livechat/cors/message/post",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_message_post(
        self,
        guest_token,
        thread_model,
        thread_id,
        post_data,
        context=None,
        **kwargs,
    ):
        return self.mail_message_post(thread_model, thread_id, post_data, context, **kwargs)

    @route(
        "/im_livechat/cors/message/update_content",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_message_update_content(self, guest_token, message_id, update_data, **kwargs):
        return self.mail_message_update_content(message_id, update_data, **kwargs)
