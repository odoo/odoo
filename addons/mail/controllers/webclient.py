# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class WebclientController(http.Controller):
    @http.route("/mail/init_messaging", methods=["POST"], type="json", auth="public")
    def mail_init_messaging(self):
        if not request.env.user.sudo()._is_public():
            return request.env.user.sudo(request.env.user.has_group("base.group_portal"))._init_messaging()
        guest = request.env["mail.guest"]._get_guest_from_request(request)
        if guest:
            return guest.sudo()._init_messaging()
        raise NotFound()

    @http.route("/mail/load_message_failures", methods=["POST"], type="json", auth="user")
    def mail_load_message_failures(self):
        return request.env.user.partner_id._message_fetch_failed()
