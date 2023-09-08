# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.message_reaction import MessageReactionController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class LivechatReactionController(MessageReactionController):
    @route("/mail/message/reaction", cors="*")
    @add_guest_to_context
    def mail_message_add_reaction(self, message_id, content, action):
        return super().mail_message_add_reaction(message_id, content, action)
