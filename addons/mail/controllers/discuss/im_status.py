# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

class ImStatusController(http.Controller):
    @http.route("/mail/force_im_status", methods=["POST"], type="jsonrpc", auth="user")
    def force_im_status(self, status):
        user = request.env.user
        user.forced_im_status = status
        user._bus_send(
            "bus.bus/im_status_updated",
            {"im_status": status or user.im_status, "partner_id": user.partner_id.id},
            subchannel="presence",
        )
