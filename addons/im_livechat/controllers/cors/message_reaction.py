# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.mail.controllers.message_reaction import MessageReactionController


class LivechatMessageReactionController(MessageReactionController):
    @route(
        "/im_livechat/cors/message/reaction",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_message_reaction(self, guest_token, message_id, content, action, **kwargs):
        return self.mail_message_reaction(message_id, content, action, **kwargs)
