# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

from datetime import datetime, timedelta, time


class ImStatusController(http.Controller):
    @http.route("/mail/im_status", methods=["POST"], type="json", auth="user")
    def set_im_status(self, action):
        user = request.env.user
        user.forced_im_status = None if action == "online" else action
        user._bus_send(
            "bus.bus/im_status_updated",
            {"im_status": action, "partner_id": user.partner_id.id},
            subchannel="presence",
        )

    @http.route("/mail/custom_status", methods=["POST"], type="json", auth="user")
    def set_custom_status(self, custom_status, reset_after):
        user = request.env.user
        user.custom_status = custom_status
        match reset_after:
            case "today":
                user.reset_custom_status_datetime = datetime.combine(
                    datetime.utcnow().date() + timedelta(days=1), time()
                )
            case "1_hour":
                user.reset_custom_status_datetime = datetime.utcnow() + timedelta(hours=1)
            case "4_hour":
                user.reset_custom_status_datetime = datetime.utcnow() + timedelta(hours=4)
            case "never":
                user.reset_custom_status_datetime = None
        if reset_after != "never":
            request.env.ref("mail.ir_cron_reset_custom_statuses")._trigger(
                user.reset_custom_status_datetime
            )
