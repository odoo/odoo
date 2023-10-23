from odoo import models
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _get_im_status(self, data):
        im_status = super()._get_im_status(data)
        if "mail.guest" in data:
            im_status["Persona"] += [{**g, 'type': "guest"} for g in (
                self.env["mail.guest"]
                .sudo()
                .with_context(active_test=False)
                .search_read([("id", "in", data["mail.guest"])], ["im_status"])
            )]
        return im_status

    @add_guest_to_context
    def _build_bus_channel_list(self, channels):
        channels = list(channels)  # do not alter original list
        guest_sudo = self.env["mail.guest"]._get_guest_from_context().sudo()
        discuss_channels = self.env["discuss.channel"]
        if self.env.uid and not self.env.user._is_public():
            discuss_channels = self.env.user.partner_id.channel_ids
        elif guest_sudo:
            discuss_channels = guest_sudo.channel_ids
            channels.append(guest_sudo)
        for discuss_channel in discuss_channels:
            channels.append(discuss_channel)
        return super()._build_bus_channel_list(channels)

    @add_guest_to_context
    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        super()._update_bus_presence(inactivity_period, im_status_ids_by_model)
        if not self.env.user or self.env.user._is_public():
            guest_sudo = self.env["mail.guest"]._get_guest_from_context().sudo()
            if not guest_sudo:
                return
            guest_sudo.env["bus.presence"].update_presence(
                inactivity_period,
                identity_field="guest_id",
                identity_value=guest_sudo.id,
            )
