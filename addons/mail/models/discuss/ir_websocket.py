# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from datetime import datetime, timedelta

from odoo import models
from odoo.osv import expression
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    @add_guest_to_context
    def _build_presence_channel_list(self, subscription_channels):
        str_presence_channels = {
            c for c in subscription_channels if isinstance(c, str) and c.startswith("odoo-presence-")
        }
        ids_by_model = {}
        for channel in str_presence_channels:
            model, id = channel[len("odoo-presence-"):].split("_")
            ids_by_model.setdefault(model, []).append(int(id))
            subscription_channels.remove(channel)
        channels = []
        if self.env.user and self.env.user._is_internal():
            channels += [
                (r, "presence")
                for model, ids in ids_by_model.items()
                for r in self.env[model].browse(ids)
            ]
            return channels
        self_discuss_channels = self.env["discuss.channel"]
        if self.env.user and not self.env.user._is_public():
            self_discuss_channels = self.env.user.partner_id.channel_ids
        elif guest := self.env["mail.guest"]._get_guest_from_context():
            # sudo - mail.guest: guest can access their own channels.
            self_discuss_channels = guest.sudo().channel_ids
        partner_domain = [
            ("id", "in", ids_by_model.get("res.partner")),
            ("channel_ids", "in", self_discuss_channels.ids),
        ]
        # sudo - res.partner: allow access when sharing a common channel.
        channels.extend(
            (partner, "presence") for partner in self.env["res.partner"].sudo().search(partner_domain)
        )
        guest_domain = [
            ("id", "in", ids_by_model.get("mail.guest")),
            ("channel_ids", "in", self_discuss_channels.ids)
        ]
        # sudo - mail.guest: allow access when sharing a common channel.
        channels.extend(
            (guest, "presence") for guest in self.env["mail.guest"].sudo().search(guest_domain)
        )
        return channels

    @add_guest_to_context
    def _build_bus_channel_list(self, channels):
        channels = list(channels)  # do not alter original list
        presence_channels = self._build_presence_channel_list(channels)
        discuss_channel_ids = []
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
        channels.extend([*all_user_channels, *member_specific_channels, *presence_channels])
        return super()._build_bus_channel_list(channels)

    def _dispatch_missed_presences(self, channels):
        # There is a gap between a subscription client side (which is debounced)
        # and the actual subcription thus presences can be missed. Send a
        # notification to avoid missing presences during a subscription.
        presence_channels = [c for c in channels if isinstance(c, tuple) and c[1] == "presence"]
        partners = self.env["res.partner"].browse(
            [p.id for p, _ in presence_channels if isinstance(p, self.pool["res.partner"])]
        )
        guest_ids = [g.id for g, _ in presence_channels if isinstance(g, self.pool["mail.guest"])]
        domain = expression.AND(
            [
                [("last_poll", ">", datetime.now() - timedelta(seconds=2))],
                expression.OR(
                    [
                        # sudo: res.partner - can access users of partner channels to find
                        # their presences as those channels were already verified during
                        # `_build_bus_channel_list`.
                        [("user_id", "in", partners.with_context(active_test=False).sudo().user_ids.ids)],
                        [("guest_id", "in", guest_ids)]
                    ]
                ),
            ]
        )
        # sudo: mail.presence - can access presences linked to presence channels.
        missed_presences = self.env["mail.presence"].sudo().search(domain)
        bus_target = (
            self.env.user.partner_id
            if self.env.user and not self.env.user._is_public()
            else self.env["mail.guest"]._get_guest_from_context()
        )
        if bus_target:
            missed_presences._send_presence(bus_target=bus_target)

    def _subscribe(self, og_data):
        data = super()._subscribe(og_data)
        self._dispatch_missed_presences(data["channels"])

    @add_guest_to_context
    def _update_bus_presence(self, inactivity_period):
        super()._update_bus_presence(inactivity_period)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user and self.env.user._is_public() and not guest:
            return
        # sudo: mail.presence - user/guest can access their own presence
        self.env["mail.presence"].sudo().update_presence(
            inactivity_period,
            identity_field="guest_id" if guest else "user_id",
            identity_value=guest.id if guest else self.env.user.id,
        )

    def _on_websocket_closed(self, cookies):
        super()._on_websocket_closed(cookies)
        domain = []
        if self.env.user and not self.env.user._is_public():
            domain.append(("user_id", "=", self.env.uid))
        else:
            token = cookies.get(self.env["mail.guest"]._cookie_name, "")
            if guest := self.env["mail.guest"]._get_guest_from_token(token):
                domain.append(("guest_id", "=", guest.id))
        if domain:
            # sudo: mail.presence - user/guest can access their own presence
            self.env["mail.presence"].sudo().search(domain).status = "offline"
