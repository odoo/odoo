# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.mail.controllers import message_reaction
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.portal.models.mail_thread import check_portal_access_token


class MessageReactionController(message_reaction.MessageReactionController):

    @http.route("/mail/message/reaction", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    @check_portal_access_token
    def mail_message_add_reaction(self, message_id, content, action):
        return super().mail_message_add_reaction(message_id, content, action)
