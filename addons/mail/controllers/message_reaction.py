# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store


class MessageReactionController(http.Controller):
    @http.route("/mail/message/reaction", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_message_reaction(self, message_id, content, action):
        message = request.env["mail.message"].browse(int(message_id)).exists()
        if not message._validate_access_for_current_persona("write"):
            raise NotFound()
        partner, guest = request.env["res.partner"]._get_current_persona()
        if not partner and not guest:
            raise NotFound()
        store = Store()
        # sudo: mail.message - access mail.message.reaction through an accessible message is allowed
        message.sudo()._message_reaction(content, action, partner, guest, store)
        return store.get_result()
