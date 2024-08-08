# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteChatRoomController(http.Controller):

    @http.route(["/chat_room/is_full"], type="json", auth="public")
    def chat_room_is_full(self, chat_room_name):
        return self._chat_room_exists(chat_room_name).is_full

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _chat_room_exists(self, chat_room_name):
        return request.env["chat.room"].sudo().search([("name", "=", chat_room_name)], limit=1)
