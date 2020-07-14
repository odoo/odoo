# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from werkzeug.exceptions import Forbidden, NotFound

from odoo import exceptions, http
from odoo.http import request
from odoo.addons.website_event_track.controllers.main import WebsiteEventTrackController
from odoo.modules.module import get_module_resource
from odoo.tools import ustr
from odoo.tools.translate import _


class WebsiteEventTrackOnlineController(WebsiteEventTrackController):

    def _can_access_track(self, track_id):
        track = request.env['event.track'].browse(track_id).exists()
        if not track:
            raise NotFound()
        try:
            track.check_access_rule('read')
        except exceptions.AccessError:
            raise Forbidden()

        track_sudo = track.sudo()
        if not track_sudo.event_id.can_access_from_current_website():
            raise NotFound()

        return track_sudo

    @http.route("/event/track/toggle_wishlist", type="json", auth="public", website=True)
    def track_wishlist_toggle(self, track_id, set_wishlisted):
        """ Wishlist a track for current visitor. Track visitor is created or updated
        if it already exists. Exception made if un-wishlisting and no track_visitor
        record found (should not happen unless manually done).

        :param boolean set_wishlisted: if True, set as a wishlist, otherwise un-whichlist
          track;
        """
        track_sudo = self._can_access_track(track_id)

        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._update_visitor_last_visit()

        event_track_partner = track_sudo._get_event_track_visitors(visitor_sudo, force_create=set_wishlisted)
        if not event_track_partner or event_track_partner.is_wishlisted == set_wishlisted:  # ignore if new state = old state
            return {'error': 'ignored'}

        event_track_partner.is_wishlisted = set_wishlisted

        return {'wishlisted': set_wishlisted}

    @http.route('/event/manifest.webmanifest', type='http', auth='public', methods=['GET'], website=True)
    def webmanifest(self):
        """ Returns a WebManifest describing the metadata associated with a web application.
        Using this metadata, user agents can provide developers with means to create user 
        experiences that are more comparable to that of a native application.
        """
        company = request.env.company
        website = request.website
        manifest = {
            'name': _('%s Online Events') % company.name,
            'short_name': company.name,
            'description': _('%s Online Events') % company.name,
            'scope': '/event',
            'start_url': '/event',
            'display': 'standalone',
            'background_color': '#ffffff',
            'theme_color': '#875A7B',
        }
        icon_sizes = ['192x192', '512x512']
        manifest['icons'] = [{
            'src': website.image_url(website, 'app_icon', size=size),
            'sizes': size,
            'type': 'image/png',
        } for size in icon_sizes]
        body = json.dumps(manifest, default=ustr)
        response = request.make_response(body, [
            ('Content-Type', 'application/manifest+json'),
        ])
        return response

    @http.route('/event/service-worker.js', type='http', auth='public', methods=['GET'], website=True)
    def service_worker(self):
        """ Returns a ServiceWorker javascript file scoped for website_event
        """
        sw_file = get_module_resource('website_event_track_online', 'static/src/js/service_worker.js')
        with open(sw_file, 'rb') as fp:
            body = fp.read()
        response = request.make_response(body, [
            ('Content-Type', 'text/javascript'),
            ('Service-Worker-Allowed', '/event'),
        ])
        return response
