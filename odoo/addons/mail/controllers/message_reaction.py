# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class MessageReactionController(http.Controller):
    @http.route("/mail/message/reaction", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_message_add_reaction(self, message_id, content, action):
        message = request.env["mail.message"].browse(int(message_id)).exists()
        if not message._validate_access_for_current_persona("write"):
            raise NotFound()
        message.sudo()._message_reaction(content, action)
