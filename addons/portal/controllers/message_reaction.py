# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.mail.controllers import message_reaction
from odoo.addons.portal.models.mail_thread import add_portal_partner_to_context


class MessageReactionController(message_reaction.MessageReactionController):

    @http.route()
    @add_portal_partner_to_context
    def mail_message_add_reaction(self, message_id, content, action, **kwargs):
        return super().mail_message_add_reaction(message_id, content, action, **kwargs)
