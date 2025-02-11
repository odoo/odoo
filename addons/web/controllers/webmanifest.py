# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
import mimetypes

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import ustr, file_open


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
                    'url': '/web#menu_id=%s' % data.mapped('res_id')[0],
                    'description': module.summary,
                    'icons': [{
                        'sizes': '100x100',
                        'src': module.icon,
                        'type': mimetypes.guess_type(module.icon)[0] or 'image/png'
                    }]
                })
        return shortcuts

    @http.route('/web/manifest.webmanifest', type='http', auth='public', methods=['GET'])
    def webmanifest(self):
        """ Returns a WebManifest describing the metadata associated with a web application.
        Using this metadata, user agents can provide developers with means to create user
        experiences that are more comparable to that of a native application.
        """
        web_app_name = request.env['ir.config_parameter'].sudo().get_param('web.web_app_name', 'Odoo')
        manifest = {
            'name': web_app_name,
            'scope': '/web',
            'start_url': '/web',
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
        body = json.dumps(manifest, default=ustr)
        response = request.make_response(body, [
            ('Content-Type', 'application/manifest+json'),
        ])
        return response

    @http.route('/web/service-worker.js', type='http', auth='public', methods=['GET'])
    def service_worker(self):
        response = request.make_response(
            self._get_service_worker_content(),
            [
                ('Content-Type', 'text/javascript'),
                ('Service-Worker-Allowed', '/web'),
            ]
        )
        return response

    def _get_service_worker_content(self):
        """ Returns a ServiceWorker javascript file scoped for the backend (aka. '/web')
        """
        with file_open('web/static/src/service_worker.js') as f:
            body = f.read()
            return body

    def _icon_path(self):
        return 'web/static/img/odoo-icon-192x192.png'

    @http.route('/web/offline', type='http', auth='public', methods=['GET'])
    def offline(self):
        """ Returns the offline page delivered by the service worker """
        return request.render('web.webclient_offline', {
            'odoo_icon': base64.b64encode(file_open(self._icon_path(), 'rb').read())
        })
