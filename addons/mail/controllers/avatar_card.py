# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class AvatarCardController(http.Controller):
    def _get_user_fields(self):
        return ["name", "email", "phone", "im_status", "share"]

    @http.route("/mail/avatar_card/get_user_info", methods=["POST"], type="json", auth="user")
    def mail_avatar_card_get_user_info(self, user_id):
        fields = self._get_user_fields()
        user = request.env["res.users"].search_read(
            domain=[("id", "=", user_id)],
            fields=fields,
            limit=1,
        )
        if not user:
            raise NotFound()
        return user[0]
