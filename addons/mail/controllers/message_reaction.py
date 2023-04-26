# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class MessageReactionController(http.Controller):
    @http.route("/mail/message/add_reaction", methods=["POST"], type="json", auth="public")
    def mail_message_add_reaction(self, message_id, content):
        guest_sudo = request.env["mail.guest"]._get_guest_from_request(request).sudo()
        message_sudo = guest_sudo.env["mail.message"].browse(int(message_id)).exists()
        if not message_sudo:
            raise NotFound()
        if request.env.user.sudo()._is_public():
            if (
                not guest_sudo
                or not message_sudo.model == "discuss.channel"
                or message_sudo.res_id not in guest_sudo.channel_ids.ids
            ):
                raise NotFound()
            message_sudo._message_add_reaction(content=content)
            guests = [("insert", {"id": guest_sudo.id})]
            partners = []
        else:
            message_sudo.sudo(False)._message_add_reaction(content=content)
            guests = []
            partners = [("insert", {"id": request.env.user.partner_id.id})]
        reactions = message_sudo.env["mail.message.reaction"].search(
            [("message_id", "=", message_sudo.id), ("content", "=", content)]
        )
        return {
            "id": message_sudo.id,
            "messageReactionGroups": [
                (
                    "insert" if len(reactions) > 0 else "insert-and-unlink",
                    {
                        "content": content,
                        "count": len(reactions),
                        "guests": guests,
                        "message": {"id": message_sudo.id},
                        "partners": partners,
                    },
                )
            ],
        }

    @http.route("/mail/message/remove_reaction", methods=["POST"], type="json", auth="public")
    def mail_message_remove_reaction(self, message_id, content):
        guest_sudo = request.env["mail.guest"]._get_guest_from_request(request).sudo()
        message_sudo = guest_sudo.env["mail.message"].browse(int(message_id)).exists()
        if not message_sudo:
            raise NotFound()
        if request.env.user.sudo()._is_public():
            if (
                not guest_sudo
                or not message_sudo.model == "discuss.channel"
                or message_sudo.res_id not in guest_sudo.channel_ids.ids
            ):
                raise NotFound()
            message_sudo._message_remove_reaction(content=content)
            guests = [("insert-and-unlink", {"id": guest_sudo.id})]
            partners = []
        else:
            message_sudo.sudo(False)._message_remove_reaction(content=content)
            guests = []
            partners = [("insert-and-unlink", {"id": request.env.user.partner_id.id})]
        reactions = message_sudo.env["mail.message.reaction"].search(
            [("message_id", "=", message_sudo.id), ("content", "=", content)]
        )
        return {
            "id": message_sudo.id,
            "messageReactionGroups": [
                (
                    "insert" if len(reactions) > 0 else "insert-and-unlink",
                    {
                        "content": content,
                        "count": len(reactions),
                        "guests": guests,
                        "message": {"id": message_sudo.id},
                        "partners": partners,
                    },
                )
            ],
        }
