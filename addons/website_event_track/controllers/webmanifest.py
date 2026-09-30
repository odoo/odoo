# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http
from odoo.http import request
from odoo.tools.misc import file_open
from odoo.tools.translate import _


class TrackManifest(http.Controller):

    @http.route('/event/manifest.webmanifest', type='http', auth='public', methods=['GET'], website=True, sitemap=False, readonly=True)
    def webmanifest(self):
        """ Returns a WebManifest describing the metadata associated with a web application.
        Using this metadata, user agents can provide developers with means to create user 
        experiences that are more comparable to that of a native application.
        """
        website = request.website
        manifest = {
            'name': website.events_app_name,
            'short_name': website.events_app_name,
            'description': _('%s Online Events Application') % website.company_id.name,
            'scope': request.env['ir.http']._url_for('/event'),
            'start_url': request.env['ir.http']._url_for('/event'),
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
        body = json.dumps(manifest)
        response = request.make_response(body, [
            ('Content-Type', 'application/manifest+json'),
        ])
        return response

    @http.route('/event/service-worker.js', type='http', auth='public', methods=['GET'], website=True, sitemap=False, readonly=True)
    def service_worker(self):
        """ Returns a ServiceWorker javascript file scoped for website_event
        """
        with file_open('website_event_track/static/src/js/service_worker.js', 'r') as fp:
            body = fp.read()
        js_cdn_url = 'undefined'
        if request.website.cdn_activated:
            cdn_url = request.website.cdn_url.replace('"','%22').replace('\x5c','%5C')
            js_cdn_url = '"%s"' % cdn_url
        body = body.replace('__ODOO_CDN_URL__', js_cdn_url)
        response = request.make_response(body, [
            ('Content-Type', 'text/javascript'),
            ('Service-Worker-Allowed', request.env['ir.http']._url_for('/event')),
        ])
        return response

    @http.route('/event/offline', type='http', auth='public', methods=['GET'], website=True, sitemap=False, readonly=True)
    def offline(self):
        """ Returns the offline page used by the 'website_event' PWA
        """
        return request.render('website_event_track.pwa_offline')
