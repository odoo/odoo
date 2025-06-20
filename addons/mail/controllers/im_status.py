# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request


class ImStatusController(http.Controller):
    @http.route("/mail/set_manual_im_status", methods=["POST"], type="jsonrpc", auth="user")
    def set_manual_im_status(self, status):
        if status not in ["online", "away", "busy", "offline"]:
            raise ValueError(_("Unexpected IM status %(status)s", status=status))
        user = request.env.user
        user.manual_im_status = False if status == "online" else status
        user._bus_send(
            "bus.bus/im_status_updated",
            {
                "debounce": False,
                "im_status": user.partner_id.im_status,
                "partner_id": user.partner_id.id,
            },
            subchannel="presence",
        )
