# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.mail.controllers.message_reaction import MessageReactionController
from odoo.addons.portal.utils import get_portal_partner


class PortalMessageReactionController(MessageReactionController):
    def _get_reaction_author(self, message, **kwargs):
        partner, guest = super()._get_reaction_author(message, **kwargs)
        if not partner and message.model and message.res_id:
            thread = request.env[message.model].browse(message.res_id)
            if partner := get_portal_partner(
                thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
            ):
                guest = request.env["mail.guest"]
        return partner, guest
