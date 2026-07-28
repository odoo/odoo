# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class GuestController(http.Controller):
    @http.route("/mail/guest/update_name", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_guest_update_name(self, guest_id, name):
        guest = request.env["mail.guest"]._get_guest_from_context()
        guest_to_rename_sudo = guest.env["mail.guest"].browse(guest_id).sudo().exists()
        if not guest_to_rename_sudo:
            raise NotFound()
        if guest_to_rename_sudo != guest and not request.env.user._is_admin():
            raise NotFound()
        guest_to_rename_sudo._update_name(name)
