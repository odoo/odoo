import base64
import binascii
import hmac
from urllib.parse import urlencode

import requests

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    event_count = fields.Integer(
        string="# Events",
        compute="_compute_event_count",
        groups="event.group_event_registration_desk",
    )
    static_map_url = fields.Char(compute="_compute_static_map_url")
    static_map_url_is_valid = fields.Boolean(compute="_compute_static_map_url_is_valid")

    def _compute_event_count(self):
        """Count the events each partner attends, its child contacts included.

        One grouped read plus one query per level of the contact hierarchy,
        instead of a ``child_of`` search per record: ``res.partner`` is not a
        ``_parent_store``, so the ancestors are walked rather than read off a
        materialised path.
        """
        self.event_count = 0
        if not self.ids:
            return
        events_per_attendee = {}
        for attendee, event in self.env["event.registration"]._read_group(
            domain=[("partner_id", "child_of", self.ids)],
            groupby=["partner_id", "event_id"],
        ):
            events_per_attendee.setdefault(attendee.id, set()).add(event.id)
        if not events_per_attendee:
            return

        # walk up to whichever records of self each attendee belongs to
        parent_of = {}
        frontier = self.browse(events_per_attendee)
        while frontier:
            next_frontier = self.browse()
            for partner in frontier:
                parent_of[partner.id] = partner.parent_id.id
                if partner.parent_id and partner.parent_id.id not in parent_of:
                    next_frontier |= partner.parent_id
            frontier = next_frontier

        events_per_partner = {partner_id: set() for partner_id in self.ids}
        for attendee_id, event_ids in events_per_attendee.items():
            node = attendee_id
            while node:
                if node in events_per_partner:
                    events_per_partner[node] |= event_ids
                node = parent_of.get(node)
        for partner in self:
            partner.event_count = len(events_per_partner[partner.id])

    @api.depends("zip", "city", "country_id", "street")
    def _compute_static_map_url(self):
        for partner in self:
            partner.static_map_url = partner._google_map_signed_img(
                zoom=13, width=598, height=200
            )

    @api.depends("static_map_url")
    def _compute_static_map_url_is_valid(self):
        """Compute whether the link is valid.

        This should only remain valid for a relatively short time.
        Here, for the duration it is in cache.
        """
        session = self.env["ir.egress"].session(purpose="static_map")
        for partner in self:
            url = partner.static_map_url
            if not url:
                partner.static_map_url_is_valid = False
                continue

            is_valid = False
            # If the response isn't strictly successful, assume invalid url
            try:
                res = session.get(url, timeout=2)
                if res.ok and not res.headers.get("X-Staticmap-API-Warning"):
                    is_valid = True
            except requests.exceptions.RequestException:
                pass

            partner.static_map_url_is_valid = is_valid

    def action_event_view(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "event.action_event_view"
        )
        action["context"] = {}
        action["domain"] = [("registration_ids.partner_id", "child_of", self.ids)]
        return action

    @api.model
    def _decode_google_maps_secret(self, secret):
        """Decode a Google URL-signing secret, or None if it is not valid base64.

        Google issues these unpadded, so the padding is added here rather than
        expected from the user; settings validation and signing must agree on
        that or a valid secret is refused at one end and accepted at the other.
        """
        try:
            return base64.urlsafe_b64decode(secret + "====")
        except binascii.Error:
            return None

    def _google_map_signed_img(self, zoom=13, width=298, height=298):
        """Create a signed static image URL for the location of this partner."""
        GOOGLE_MAPS_STATIC_API_KEY = self.env[
            "credential.credential"
        ]._get_system_secret("google_maps.signed_static_api_key")
        GOOGLE_MAPS_STATIC_API_SECRET = self.env[
            "credential.credential"
        ]._get_system_secret("google_maps.signed_static_api_secret")
        if not GOOGLE_MAPS_STATIC_API_KEY or not GOOGLE_MAPS_STATIC_API_SECRET:
            return None
        api_secret_bytes = self._decode_google_maps_secret(
            GOOGLE_MAPS_STATIC_API_SECRET
        )
        if api_secret_bytes is None:
            return None
        # generate signature as per https://developers.google.com/maps/documentation/maps-static/digital-signature#server-side-signing
        location_string = f"{self.street}, {self.city} {self.zip}, {(self.country_id and self.country_id.display_name) or ''}"
        params = {
            "center": location_string,
            "markers": f"size:mid|{location_string}",
            "size": f"{width}x{height}",
            "zoom": zoom,
            "sensor": "false",
            "key": GOOGLE_MAPS_STATIC_API_KEY,
        }
        unsigned_path = "/maps/api/staticmap?" + urlencode(params)
        url_signature_bytes = hmac.digest(
            api_secret_bytes, unsigned_path.encode(), "sha1"
        )
        params["signature"] = base64.urlsafe_b64encode(url_signature_bytes)

        return "https://maps.googleapis.com/maps/api/staticmap?" + urlencode(params)
