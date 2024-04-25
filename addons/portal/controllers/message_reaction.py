# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers import message_reaction
from odoo.addons.portal.models.mail_thread import check_portal_access


class MessageReactionController(message_reaction.MessageReactionController):

    @http.route()
    @check_portal_access
    def mail_message_add_reaction(self, message_id, content, action):
        message_sudo = request.env["mail.message"].sudo().browse(int(message_id)).exists()
        thread = message_sudo.env[message_sudo.model].search([("id", "=", message_sudo.res_id)])
        if thread._get_portal_access():
            return message_sudo._message_reaction(content, action)
        return super().mail_message_add_reaction(message_id, content, action)
