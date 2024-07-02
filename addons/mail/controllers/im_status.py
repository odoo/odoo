# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class ImStatusController(http.Controller):
    @http.route("/mail/im_status", methods=["POST"], type="json", auth="user")
    def set_im_status(self, action):
        user = request.env.user
        user.forced_im_status = None if action == "online" else action
        user.res_users_settings_id.mute(-1 if action == "do_not_disturb" else 0)
