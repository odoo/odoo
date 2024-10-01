from odoo import http
from odoo.http import request
from odoo.tools.misc import file_open


class POSManifest(http.Controller):

    @http.route('/pos/service-worker.js', type='http', auth='public', methods=['GET'])
    def service_worker(self):
        """ Returns Service Worker JS for POS """
        with file_open('point_of_sale/static/src/js/service_worker.js') as fp:
            body = fp.read()
        response = request.make_response(body, [
            ('Content-Type', 'text/javascript'),
            ('Service-Worker-Allowed', '/pos'),
        ])
        return response
