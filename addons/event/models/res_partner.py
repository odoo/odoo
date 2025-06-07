# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import binascii
import hmac

import requests
import werkzeug.urls

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    event_count = fields.Integer(
        '# Events', compute='_compute_event_count', groups='event.group_event_registration_desk')
    static_map_url = fields.Char(compute="_compute_static_map_url")
    static_map_url_is_valid = fields.Boolean(compute="_compute_static_map_url_is_valid")

    def _compute_event_count(self):
        self.event_count = 0
        for partner in self:
            partner.event_count = self.env['event.event'].search_count([('registration_ids.partner_id', 'child_of', partner.ids)])

    @api.depends('zip', 'city', 'country_id', 'street')
    def _compute_static_map_url(self):
        for partner in self:
            partner.static_map_url = partner._google_map_signed_img(zoom=13, width=598, height=200)

    @api.depends('static_map_url')
    def _compute_static_map_url_is_valid(self):
        """Compute whether the link is valid.

        This should only remain valid for a relatively short time.
        Here, for the duration it is in cache.
        """
        session = requests.Session()
        for partner in self:
            url = partner.static_map_url
            if not url:
                partner.static_map_url_is_valid = False
                continue

            is_valid = False
            # If the response isn't strictly successful, assume invalid url
            try:
                res = session.get(url, timeout=2)
                if res.ok and not res.headers.get('X-Staticmap-API-Warning'):
                    is_valid = True
            except requests.exceptions.RequestException:
                pass

            partner.static_map_url_is_valid = is_valid

    def action_event_view(self):
        action = self.env["ir.actions.actions"]._for_xml_id("event.action_event_view")
        action['context'] = {}
        action['domain'] = [('registration_ids.partner_id', 'child_of', self.ids)]
        return action

    def _google_map_signed_img(self, zoom=13, width=298, height=298):
        """Create a signed static image URL for the location of this partner."""
        GOOGLE_MAPS_STATIC_API_KEY = self.env['ir.config_parameter'].sudo().get_param('google_maps.signed_static_api_key')
        GOOGLE_MAPS_STATIC_API_SECRET = self.env['ir.config_parameter'].sudo().get_param('google_maps.signed_static_api_secret')
        if not GOOGLE_MAPS_STATIC_API_KEY or not GOOGLE_MAPS_STATIC_API_SECRET:
            return None
        # generate signature as per https://developers.google.com/maps/documentation/maps-static/digital-signature#server-side-signing
        location_string = f"{self.street}, {self.city} {self.zip}, {self.country_id and self.country_id.display_name or ''}"
        params = {
            'center': location_string,
            'markers': f'size:mid|{location_string}',
            'size': f"{width}x{height}",
            'zoom': zoom,
            'sensor': "false",
            'key': GOOGLE_MAPS_STATIC_API_KEY,
        }
        unsigned_path = '/maps/api/staticmap?' + werkzeug.urls.url_encode(params)
        try:
            api_secret_bytes = base64.urlsafe_b64decode(GOOGLE_MAPS_STATIC_API_SECRET + "====")
        except binascii.Error:
            return None
        url_signature_bytes = hmac.digest(api_secret_bytes, unsigned_path.encode(), 'sha1')
        params['signature'] = base64.urlsafe_b64encode(url_signature_bytes)

        return 'https://maps.googleapis.com/maps/api/staticmap?' + werkzeug.urls.url_encode(params)
