# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import mimetypes

from urllib.parse import unquote, urlencode

from odoo import http, modules
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import file_open, file_path, image_process


class WebManifest(http.Controller):

    def _get_shortcuts(self):
        module_names = ['mail', 'crm', 'project', 'project_todo']
        try:
            module_ids = request.env['ir.module.module'].search([('state', '=', 'installed'), ('name', 'in', module_names)]) \
                                                        .sorted(key=lambda r: module_names.index(r["name"]))
        except AccessError:
            return []
        menu_roots = request.env['ir.ui.menu'].get_user_roots()
        datas = request.env['ir.model.data'].sudo().search([('model', '=', 'ir.ui.menu'),
                                                         ('res_id', 'in', menu_roots.ids),
                                                         ('module', 'in', module_names)])
        shortcuts = []
        for module in module_ids:
            data = datas.filtered(lambda res: res.module == module.name)
            if data:
                shortcuts.append({
                    'name': module.display_name,
                    'url': '/odoo?menu_id=%s' % data.mapped('res_id')[0],
                    'description': module.summary,
                    'icons': [{
                        'sizes': '100x100',
                        'src': module.icon,
                        'type': mimetypes.guess_type(module.icon)[0] or 'image/png'
                    }]
                })
        return shortcuts

    def _get_webmanifest(self):
        web_app_name = request.env['ir.config_parameter'].sudo().get_param('web.web_app_name', 'Odoo')
        manifest = {
            'name': web_app_name,
            'scope': '/odoo',
            'start_url': '/odoo',
            'display': 'standalone',
            'background_color': '#714B67',
            'theme_color': '#714B67',
            'prefer_related_applications': False,
        }
        icon_sizes = ['192x192', '512x512']
        manifest['icons'] = [{
            'src': '/web/static/img/odoo-icon-%s.png' % size,
            'sizes': size,
            'type': 'image/png',
        } for size in icon_sizes]
        manifest['shortcuts'] = self._get_shortcuts()
        return manifest

    @http.route('/web/manifest.webmanifest', type='http', auth='public', methods=['GET'], readonly=True)
    def webmanifest(self):
        """ Returns a WebManifest describing the metadata associated with a web application.
        Using this metadata, user agents can provide developers with means to create user
        experiences that are more comparable to that of a native application.
        """
        return request.make_json_response(self._get_webmanifest(), {
            'Content-Type': 'application/manifest+json'
        })

    @http.route('/web/service-worker.js', type='http', auth='public', methods=['GET'], readonly=True)
    def service_worker(self):
        response = request.make_response(
            self._get_service_worker_content(),
            [
                ('Content-Type', 'text/javascript'),
                ('Service-Worker-Allowed', '/odoo'),
            ]
        )
        return response

    def _get_service_worker_content(self):
        """ Returns a ServiceWorker javascript file scoped for the backend (aka. '/odoo')
        """
        with file_open('web/static/src/service_worker.js') as f:
            body = f.read()
            return body

    def _icon_path(self):
        return 'web/static/img/odoo-icon-192x192.png'

    @http.route('/odoo/offline', type='http', auth='public', methods=['GET'], readonly=True)
    def offline(self):
        """ Returns the offline page delivered by the service worker """
        return request.render('web.webclient_offline', {
            'odoo_icon': base64.b64encode(file_open(self._icon_path(), 'rb').read())
        })

    @http.route('/scoped_app', type='http', auth='public', methods=['GET'])
    def scoped_app(self, app_id, path='', app_name=''):
        """ Returns the app shortcut page to install the app given in parameters """
        app_name = unquote(app_name) if app_name else self._get_scoped_app_name(app_id)
        path = f"/{unquote(path)}"
        scoped_app_values = {
            'app_id': app_id,
            'apple_touch_icon': '/web/static/img/odoo-icon-ios.png',
            'app_name': app_name,
            'path': path,
            'safe_manifest_url': "/web/manifest.scoped_app_manifest?" + urlencode({
                'app_id': app_id,
                'path': path,
                'app_name': app_name
            })
        }
        return request.render('web.webclient_scoped_app', scoped_app_values)

    @http.route('/scoped_app_icon_png', type='http', auth='public', methods=['GET'])
    def scoped_app_icon_png(self, app_id, add_padding=False):
        """ Returns an app icon created with a fixed size in PNG. It is required for Safari PWAs """
        # To begin, we take the first icon available for the app
        app_icon = self._get_scoped_app_icons(app_id)[0]

        if app_icon['type'] == "image/svg+xml":
            # We don't handle SVG images here, let's look for the module icon if possible
            manifest = modules.module.get_manifest(app_id)
            add_padding = True
            if len(manifest) > 0 and manifest['icon']:
                icon_src = manifest['icon']
            else:
                icon_src = f"/{self._icon_path()}"
        else:
            icon_src = app_icon['src']
            if not add_padding:
                # A valid icon is explicitly provided, we can use it directly
                return request.redirect(app_icon['src'])

        # Now that we have the image source, we can generate a PNG image
        with file_open(icon_src.removeprefix('/'), 'rb') as file:
            image = image_process(file.read(), size=(180, 180), expand=True, colorize=(255, 255, 255), padding=16)
        return request.make_response(image, headers=[('Content-Type', 'image/png')])

    @http.route('/web/manifest.scoped_app_manifest', type='http', auth='public', methods=['GET'])
    def scoped_app_manifest(self, app_id, path, app_name=''):
        """ Returns a WebManifest dedicated to the scope of the given app. A custom scope and start
            url are set to make sure no other installed PWA can overlap the scope (e.g. /odoo)
        """
        path = unquote(path)
        app_name = unquote(app_name) if app_name else self._get_scoped_app_name(app_id)
        webmanifest = {
            'icons': self._get_scoped_app_icons(app_id),
            'name': app_name,
            'scope': path,
            'start_url': path,
            'display': 'standalone',
            'background_color': '#714B67',
            'theme_color': '#714B67',
            'prefer_related_applications': False,
            'shortcuts': self._get_scoped_app_shortcuts(app_id)
        }
        return request.make_json_response(webmanifest, {
            'Content-Type': 'application/manifest+json'
        })

    def _get_scoped_app_shortcuts(self, app_id):
        return []

    def _get_scoped_app_name(self, app_id):
        manifest = modules.module.get_manifest(app_id)
        if manifest:
            return manifest['name']
        return app_id

    def _get_scoped_app_icons(self, app_id):
        try:
            file_path(f'{app_id}/static/description/icon.svg')
            src = f'{app_id}/static/description/icon.svg'
        except FileNotFoundError:
            src = self._icon_path()
        return [{
            'src': f"/{src}",
            'sizes': 'any',
            'type': mimetypes.guess_type(src)[0] or 'image/png'
        }]
