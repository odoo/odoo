from odoo import models
from odoo.http import request
from odoo.addons.bus.websocket import wsrequest


class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _build_bus_channel_list(self, channels):
        #  This method can either be called due to an http or a
        #  websocket request. The request itself is necessary to
        #  retrieve the current guest. Let's retrieve the proper
        #  request.
        req = request or wsrequest
        channels = list(channels)  # do not alter original list
        guest_sudo = self.env['mail.guest']._get_guest_from_request(req).sudo()
        mail_channels = self.env['mail.channel']
        if self.env.uid:
            partner = self.env.user.partner_id
            mail_channels = partner.channel_ids
            channels.append(partner)
        elif guest_sudo:
            mail_channels = guest_sudo.channel_ids
            channels.append(guest_sudo)
        for mail_channel in mail_channels:
            channels.append(mail_channel)
        return super()._build_bus_channel_list(channels)

    def _update_bus_presence(self, inactivity_period):
        super()._update_bus_presence(inactivity_period)
        if not self.env.uid:
            #  This method can either be called due to an http or a
            #  websocket request. The request itself is necessary to
            #  retrieve the current guest. Let's retrieve the proper
            #  request.
            req = request or wsrequest
            guest_sudo = self.env['mail.guest']._get_guest_from_request(req).sudo()
            if not guest_sudo:
                return
            guest_sudo.env['bus.presence'].update(inactivity_period, identity_field='guest_id', identity_value=guest_sudo.id)
