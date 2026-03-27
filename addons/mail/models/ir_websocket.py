# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta

from odoo import models
from odoo.fields import Domain
from odoo.addons.mail.tools.discuss import add_guest_to_context
from odoo.tools.misc import verify_limited_field_access_token

PRESENCE_CHANNEL_PREFIX = "odoo-presence-"
PRESENCE_CHANNEL_REGEX = re.compile(
    rf"{PRESENCE_CHANNEL_PREFIX}"
    r"(?P<model>res\.partner|mail\.guest)_(?P<record_id>\d+)"
    r"(?:-(?P<token>[a-f0-9]{64}o0x[a-f0-9]+))?$"
)
_logger = logging.getLogger(__name__)


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

    def _prepare_subscribe_data(self, channels, last):
        data = super()._prepare_subscribe_data(channels, last)
        model_ids_to_token = defaultdict(dict)
        for channel in channels:
            if not isinstance(channel, str) or not channel.startswith(PRESENCE_CHANNEL_PREFIX):
                continue
            data["channels"].discard(channel)
            if not (match := re.match(PRESENCE_CHANNEL_REGEX, channel)):
                _logger.warning("Malformed presence channel: %s", channel)
                continue
            model, record_id, token = match.groups()
            model_ids_to_token[model][int(record_id)] = token or ""
        # sudo - res.partner, mail.guest: can access presence targets to decide whether
        # the current user is allowed to read it or not.
        partner_ids = model_ids_to_token["res.partner"].keys()
        partners = (
            self.env["res.partner"]
            .with_context(active_test=False)
            .sudo()
            .search([("id", "in", partner_ids)])
            .sudo(False)
        )
        partner, guest = self.env["res.partner"]._get_current_persona()
        allowed_partners = (
            partners.filtered(
                lambda p: verify_limited_field_access_token(
                    p, "im_status", model_ids_to_token["res.partner"][p.id], scope="mail.presence"
                )
                or p.has_access("read")
            )
            | partner
        )
        guest_ids = model_ids_to_token["mail.guest"].keys()
        guests = self.env["mail.guest"].sudo().search([("id", "in", guest_ids)]).sudo(False)
        allowed_guests = (
            guests.filtered(
                lambda g: verify_limited_field_access_token(
                    g, "im_status", model_ids_to_token["mail.guest"][g.id], scope="mail.presence"
                )
                or g.has_access("read")
            )
            | guest
        )
        data["channels"].update((partner, "presence") for partner in allowed_partners)
        data["channels"].update((guest, "presence") for guest in allowed_guests)
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
        # sudo: mail.presence: access to presence was validated with access token.
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
