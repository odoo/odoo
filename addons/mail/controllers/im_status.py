# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, http

from odoo.addons.mail.tools.discuss import mail_route, Store

STATUS_MESSAGE_MAX_LENGTH = 100


class ImStatusController(http.Controller):
    @mail_route("/mail/set_manual_im_status", methods=["POST"], type="jsonrpc", auth="user")
    def set_manual_im_status(self, status):
        if status not in ["online", "away", "busy", "offline"]:
            raise ValueError(_("Unexpected IM status %(status)s", status=status))
        self.env.user.manual_im_status = False if status == "online" else status
        Store(bus_channel=self.env.user, bus_subchannel="presence").add(
            self.env.user,
            "_store_manual_im_status_fields",
        )

    @mail_route("/mail/set_status_message", methods=["POST"], type="jsonrpc", auth="user")
    def set_status_message(self, message):
        if not isinstance(message, str):
            raise TypeError(_("Unexpected status message"))
        self.env.user.status_message = message.strip()[:STATUS_MESSAGE_MAX_LENGTH] or False
        Store(bus_channel=self.env.user, bus_subchannel="presence").add(
            self.env.user, ["status_message"]
        )
