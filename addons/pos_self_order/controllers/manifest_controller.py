# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json

from odoo import http
from odoo.http import request
from odoo.tools import ustr, file_open


class PosManifest(http.Controller):

    @http.route('/pos-self/manifest/<config_id>/<access_token>', type='http', auth='public', methods=['GET'])
    def posmanifest(self, config_id, access_token):
        """ Returns a posmanifest describing the metadata associated with a web application.
        Using this metadata, user agents can provide developers with means to create user
        experiences that are more comparable to that of a native application.
        """
        config = request.env['pos.config'].search([('id', '=', config_id)], limit=1)
        company_name = config.company_id.name
        manifest = {
            'name': config.name + " (" + company_name + ")",
            'short_name': config.name + " (" + company_name + ")",
            'scope': '/pos-self',
            'start_url': '/pos-self/%s/?access_token=%s' % (config_id, access_token),
            'display': 'standalone',
            'background_color': '#FFFFFF',
            'theme_color': '#FFFFFF',
            'orientation': 'portrait-primary'
        }
        icon_sizes = ['192', '255', '512']
        manifest['icons'] = [{
            'src': self._icon_src(size),
            'sizes': size + 'x' + size,
            'type': 'image/png',
        } for size in icon_sizes]
        body = json.dumps(manifest, default=ustr)
        response = request.make_response(body, [
            ('Content-Type', 'application/manifest+json'),
        ])
        return response

    @http.route('/pos-self/service-worker.js', type='http', auth='public', methods=['GET'])
    def service_worker(self):
        response = request.make_response(
            self._get_service_worker_content(),
            [
                ('Content-Type', 'text/javascript'),
                ('Service-Worker-Allowed', '/pos-self'),
            ]
        )
        return response

    def _get_service_worker_content(self):
        """ Returns a ServiceWorker javascript file scoped for the backend (aka. '/pos-self')
        """
        with file_open('pos_self_order/static/src/service_worker.js') as f:
            body = f.read()
            return body

    def _icon_src(self, size):
        company = request.env.company
        company_id = request.env.company.id
        if not company.uses_default_logo:
            icon_src = '/web/image?model=res.company&id=%s&field=logo&crop=true&height=%s&width=%s' % (company_id, size, size)
        else:
            icon_src = '/web/static/img/odoo-icon-%sx%s.png' % (size, size)
        return icon_src

    @http.route('/pos-self/offline', type='http', auth='public', methods=['GET'])
    def offline(self):
        """ Returns the offline page delivered by the service worker """
        company = request.env.company
        return request.render('web.webclient_offline', {
            'odoo_icon': base64.b64encode(file_open('web/static/img/odoo-icon-192x192.png', 'rb').read()) if company.uses_default_logo else company.logo_web
        })
