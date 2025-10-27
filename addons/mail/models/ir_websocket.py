# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import models
from odoo.fields import Domain
from odoo.addons.mail.tools.discuss import add_guest_to_context


class IrWebsocket(models.AbstractModel):
    """Override to handle mail specific features (presence in particular)."""

    _inherit = "ir.websocket"

    def _serve_ir_websocket(self, event_name, data):
        """Override to process update_presence."""
        super()._serve_ir_websocket(event_name, data)
        if event_name == "update_presence":
            self._update_mail_presence(**data)

    @add_guest_to_context
    def _subscribe(self, og_data):
        super()._subscribe(og_data)

    @add_guest_to_context
    def _update_mail_presence(self, inactivity_period):
        partner, guest = self.env["res.partner"]._get_current_persona()
        if not partner and not guest:
            return
        self.env["mail.presence"]._try_update_presence(
            self.env.user if partner else guest, inactivity_period
        )

    def _filter_accessible_presences(self, partners, guests):
        """Filter presences that are accessible to current user."""
        if self.env.user and self.env.user._is_internal():
            return partners, guests
        return self.env["res.partner"], self.env["mail.guest"]

    def _prepare_subscribe_data(self, channels, last):
        data = super()._prepare_subscribe_data(channels, last)
        str_presence_channels = {
            c for c in channels if isinstance(c, str) and c.startswith("odoo-presence-")
        }
        simplified_presence_channels = [
            tuple(c.replace("odoo-presence-", "").split("_")) for c in str_presence_channels
        ]
        for channel in str_presence_channels:
            data["channels"].discard(channel)
        partner_ids = [int(p[1]) for p in simplified_presence_channels if p[0] == "res.partner"]
        partners = (
            self.env["res.partner"]
            .with_context(active_test=False)
            .sudo()
            .search([("id", "in", partner_ids)])
            .sudo(False)
        )
        guest_ids = [int(p[1]) for p in simplified_presence_channels if p[0] == "mail.guest"]
        guests = self.env["mail.guest"].sudo().search([("id", "in", guest_ids)]).sudo(False)
        allowed_partners, allowed_guests = self._filter_accessible_presences(partners, guests)
        partner, guest = self.env["res.partner"]._get_current_persona()
        data["channels"].update((partner, "presence") for partner in allowed_partners | partner)
        data["channels"].update((guest, "presence") for guest in allowed_guests | guest)
        # There is a gap between a subscription client side (which is debounced)
        # and the actual subcription thus presences can be missed. Send a
        # notification to avoid missing presences during a subscription.
        presence_domain = Domain("last_poll", ">", datetime.now() - timedelta(seconds=2)) & (
            Domain(
                "user_id",
                "in",
                allowed_partners.with_context(active_test=False).sudo().user_ids.ids,
            )
            | Domain("guest_id", "in", allowed_guests.ids)
        )
        # sudo: mail.presence: access to presence was validated with _filter_accessible_presences
        data["missed_presences"] = self.env["mail.presence"].sudo().search(presence_domain)
        return data

    def _after_subscribe_data(self, data):
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        if current_partner or current_guest:
            data["missed_presences"]._send_presence(bus_target=current_partner or current_guest)

    def _on_websocket_closed(self, cookies):
        super()._on_websocket_closed(cookies)
        if self.env.user and not self.env.user._is_public():
            # sudo: mail.presence - user can update their own presence
            self.env.user.sudo().presence_ids.status = "offline"
        token = cookies.get(self.env["mail.guest"]._cookie_name, "")
        if guest := self.env["mail.guest"]._get_guest_from_token(token):
        # sudo: mail.presence - guest can update their own presence
            guest.sudo().presence_ids.status = "offline"
