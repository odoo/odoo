# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from datetime import datetime, timedelta

from odoo import models
from odoo.tools import OrderedSet
from odoo.osv import expression
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class IrWebsocket(models.AbstractModel):
    _inherit = ["ir.websocket"]

    def _get_missed_presences_bus_target(self):
        if self.env.user and not self.env.user._is_public():
            return self.env.user.partner_id
        if guest := self.env["mail.guest"]._get_guest_from_context():
            return guest
        return None

    @add_guest_to_context
    def _build_presence_channel_list(self, presences):
        """
        Return the list of presences to subscribe to.

        :param typing.List[typing.Tuple[str, int]] presences: The presence
            list sent by the client where the first element is the model
            name and the second is the record id.
        """
        channels = []
        guest_ids = [int(p[1]) for p in presences if p[0] == "mail.guest"]
        if self.env.user and self.env.user._is_internal():
            channels.extend(
                (partner, "presence")
                for partner in self.env["res.partner"]
                .with_context(active_test=False)
                .search([("id", "in", [int(p[1]) for p in presences if p[0] == "res.partner"])])
            )
            channels.extend(
                (guest, "presence")
                for guest in self.env["mail.guest"].search([("id", "in", guest_ids)])
            )
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

    def _prepare_subscribe_data(self, channels, last):
        data = super()._prepare_subscribe_data(channels, last)
        str_presence_channels = {
            c for c in channels if isinstance(c, str) and c.startswith("odoo-presence-")
        }
        presence_channels = self._build_presence_channel_list(
            [tuple(c.replace("odoo-presence-", "").split("_")) for c in str_presence_channels]
        )
        # There is a gap between a subscription client side (which is debounced)
        # and the actual subcription thus presences can be missed. Send a
        # notification to avoid missing presences during a subscription.
        partners = self.env["res.partner"].browse(
            [p.id for p, _ in presence_channels if isinstance(p, self.pool["res.partner"])]
        )
        guest_ids = [g.id for g, _ in presence_channels if isinstance(g, self.pool["mail.guest"])]
        # sudo: res.partner - can acess users of partner channels to find
        # their presences as those channels were already verified during
        # `_build_bus_channel_list`.
        domain = expression.AND(
            [
                [("last_poll", ">", datetime.now() - timedelta(seconds=2))],
                expression.OR(
                    [
                        [("user_id", "in", partners.with_context(active_test=False).sudo().user_ids.ids)],
                        [("guest_id", "in", guest_ids)]
                    ]
                ),
            ]
        )
        # sudo: mail.presence: can access presences linked to presence channels.
        missed_presences = self.env["mail.presence"].sudo().search(domain)
        all_channels = OrderedSet(presence_channels)
        all_channels.update(
            self._build_bus_channel_list([c for c in channels if c not in str_presence_channels])
        )
        data.update({"channels": all_channels, "missed_presences": missed_presences})
        return data

    def _subscribe(self, og_data):
        super()._subscribe(og_data)
        data = self._prepare_subscribe_data(og_data["channels"], og_data["last"])
        if bus_target := self._get_missed_presences_bus_target():
            data["missed_presences"]._send_presence(bus_target=bus_target)

    @add_guest_to_context
    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        super()._update_bus_presence(inactivity_period, im_status_ids_by_model)
        if self.env.user and not self.env.user._is_public():
            self.env['mail.presence'].update_presence(
                inactivity_period,
                identity_field='user_id',
                identity_value=self.env.uid
            )
        else:
            guest = self.env["mail.guest"]._get_guest_from_context()
            if not guest:
                return
            # sudo: mail.presence - guests currently need sudo to write their own presence
            self.env["mail.presence"].sudo().update_presence(
                inactivity_period,
                identity_field="guest_id",
                identity_value=guest.id,
            )

    def _on_websocket_closed(self, cookies):
        super()._on_websocket_closed(cookies)
        domain = []
        mail_presence = self.env["mail.presence"]
        if self.env.user and not self.env.user._is_public():
            domain.append(("user_id", "=", self.env.uid))
        else:
            token = cookies.get(self.env["mail.guest"]._cookie_name, "")
            if guest := self.env["mail.guest"]._get_guest_from_token(token):
                domain.append(("guest_id", "=", guest.id))
                # sudo - mail.presence: guests can write their own presence
                mail_presence = mail_presence.sudo()
        if domain:
            mail_presence.search(domain).status = "offline"
