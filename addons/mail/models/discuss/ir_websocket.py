from odoo import models
from odoo.http import request
from odoo.addons.bus.websocket import wsrequest


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _get_im_status(self, data):
        im_status = super()._get_im_status(data)
        if "mail.guest" in data:
            im_status["Guest"] = (
                self.env["mail.guest"]
                .sudo()
                .with_context(active_test=False)
                .search_read([("id", "in", data["mail.guest"])], ["im_status"])
            )
        return im_status

    def _build_bus_channel_list(self, channels):
        #  This method can either be called due to an http or a
        #  websocket request. The request itself is necessary to
        #  retrieve the current guest. Let's retrieve the proper
        #  request.
        req = request or wsrequest
        channels = list(channels)  # do not alter original list
        guest_sudo = self.env["mail.guest"]._get_guest_from_request(req).sudo()
        discuss_channels = self.env["discuss.channel"]
        if req.session.uid:
            discuss_channels = self.env.user.partner_id.channel_ids
        elif guest_sudo:
            discuss_channels = guest_sudo.channel_ids
            channels.append(guest_sudo)
        for discuss_channel in discuss_channels:
            channels.append(discuss_channel)
        return super()._build_bus_channel_list(channels)

    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        super()._update_bus_presence(inactivity_period, im_status_ids_by_model)
        if not self.env.user or self.env.user._is_public():
            #  This method can either be called due to an http or a
            #  websocket request. The request itself is necessary to
            #  retrieve the current guest. Let's retrieve the proper
            #  request.
            req = request or wsrequest
            guest_sudo = self.env["mail.guest"]._get_guest_from_request(req).sudo()
            if not guest_sudo:
                return
            guest_sudo.env["bus.presence"].update_presence(
                inactivity_period,
                identity_field="guest_id",
                identity_value=guest_sudo.id,
            )
