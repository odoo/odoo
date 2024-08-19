# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _get_missed_presences_identity_domains(self, presence_channels):
        identity_domain = super()._get_missed_presences_identity_domains(presence_channels)
        if guest_ids := [
            g.id for g, _ in presence_channels if isinstance(g, self.pool["mail.guest"])
        ]:
            identity_domain.append([("guest_id", "in", guest_ids)])
        return identity_domain

    def _get_missed_presences_bus_target(self):
        if self.env.user and not self.env.user._is_public():
            return super()._get_missed_presences_bus_target()
        if guest := self.env["mail.guest"]._get_guest_from_context():
            return guest
        return None

    @add_guest_to_context
    def _build_presence_channel_list(self, presences):
        channels = super()._build_presence_channel_list(presences)
        guest_ids = [int(p[1]) for p in presences if p[0] == "mail.guest"]
        if self.env.user and self.env.user._is_internal():
            channels.extend(
                (guest, "presence")
                for guest in self.env["mail.guest"].search([("id", "in", guest_ids)])
            )
            # Partners already handled in super call (bus)
            return channels
        self_discuss_channels = self.env["discuss.channel"]
        if self.env.user and not self.env.user._is_public():
            self_discuss_channels = self.env.user.partner_id.channel_ids
        elif guest := self.env["mail.guest"]._get_guest_from_context():
            # sudo - mail.guest: guest can access their own channels.
            self_discuss_channels = guest.sudo().channel_ids
        partner_domain = [
            ("id", "in", [int(p[1]) for p in presences if p[0] == "res.partner"]),
            ("channel_ids", "in", self_discuss_channels.ids),
        ]
        # sudo - res.partner: allow access when sharing a common channel.
        channels.extend(
            (partner, "presence")
            for partner in self.env["res.partner"].sudo().search(partner_domain)
        )
        guest_domain = [("id", "in", guest_ids), ("channel_ids", "in", self_discuss_channels.ids)]
        # sudo - mail.guest: allow access when sharing a common channel.
        channels.extend(
            (guest, "presence") for guest in self.env["mail.guest"].sudo().search(guest_domain)
        )
        return channels

    @add_guest_to_context
    def _build_bus_channel_list(self, channels):
        channels = list(channels)  # do not alter original list
        discuss_channel_ids = list()
        for channel in list(channels):
            if isinstance(channel, str) and channel.startswith("mail.guest_"):
                channels.remove(channel)
                guest = self.env["mail.guest"]._get_guest_from_token(channel.split("_")[1])
                if guest:
                    self = self.with_context(guest=guest)
            if isinstance(channel, str):
                match = re.findall(r'discuss\.channel_(\d+)', channel)
                if match:
                    channels.remove(channel)
                    discuss_channel_ids.append(int(match[0]))
        guest = self.env["mail.guest"]._get_guest_from_context()
        if guest:
            channels.append(guest)
        domain = ["|", ("is_member", "=", True), ("id", "in", discuss_channel_ids)]
        all_user_channels = self.env["discuss.channel"].search(domain)
        member_specific_channels = [(c, "members") for c in all_user_channels if c.id not in discuss_channel_ids]
        channels.extend([*all_user_channels, *member_specific_channels])
        return super()._build_bus_channel_list(channels)

    @add_guest_to_context
    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        super()._update_bus_presence(inactivity_period, im_status_ids_by_model)
        if not self.env.user or self.env.user._is_public():
            guest = self.env["mail.guest"]._get_guest_from_context()
            if not guest:
                return
            # sudo: bus.presence - guests currently need sudo to write their own presence
            self.env["bus.presence"].sudo().update_presence(
                inactivity_period,
                identity_field="guest_id",
                identity_value=guest.id,
            )

    def _on_websocket_closed(self, cookies):
        super()._on_websocket_closed(cookies)
        if self.env.user and not self.env.user._is_public():
            return
        token = cookies.get(self.env["mail.guest"]._cookie_name, "")
        if guest := self.env["mail.guest"]._get_guest_from_token(token):
            # sudo - bus.presence: guests can write their own presence
            self.env["bus.presence"].sudo().search([("guest_id", "=", guest.id)]).status = "offline"
