import json

from odoo import http
from odoo.http import request
from odoo.tools.misc import file_open


class TrackManifest(http.Controller):
    @http.route(
        "/event/manifest.webmanifest",
        type="http",
        auth="public",
        methods=["GET"],
        website=True,
        sitemap=False,
        readonly=True,
    )
    def webmanifest(self):
        website = request.website
        manifest = {
            "name": website.events_app_name,
            "short_name": website.events_app_name,
            "description": request.env._("%s Online Events Application")
            % website.company_id.name,
            "scope": request.env["ir.http"]._url_for("/event"),
            "start_url": request.env["ir.http"]._url_for("/event"),
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#875A7B",
        }
        icon_sizes = ["192x192", "512x512"]
        manifest["icons"] = [
            {
                "src": website.image_url(website, "app_icon", size=size),
                "sizes": size,
                "type": "image/png",
            }
            for size in icon_sizes
        ]
        body = json.dumps(manifest)
        return request.prepare_response(
            body,
            [
                ("Content-Type", "application/manifest+json"),
            ],
        )

    @http.route(
        "/event/service-worker.js",
        type="http",
        auth="public",
        methods=["GET"],
        website=True,
        sitemap=False,
        readonly=True,
    )
    def service_worker(self):
        with file_open(
            "website_event_track/static/src/js/service_worker.js", "r"
        ) as fp:
            body = fp.read()
        js_cdn_url = "undefined"
        if request.website.cdn_activated:
            cdn_url = request.website.cdn_url.replace('"', "%22").replace("\x5c", "%5C")
            js_cdn_url = '"%s"' % cdn_url
        body = body.replace("__ODOO_CDN_URL__", js_cdn_url)
        return request.prepare_response(
            body,
            [
                ("Content-Type", "text/javascript"),
                ("Service-Worker-Allowed", request.env["ir.http"]._url_for("/event")),
            ],
        )

    @http.route(
        "/event/offline",
        type="http",
        auth="public",
        methods=["GET"],
        website=True,
        sitemap=False,
        readonly=True,
    )
    def offline(self):
        return request.render("website_event_track.pwa_offline")
