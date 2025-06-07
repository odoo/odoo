from odoo import http
from odoo.http import request, Response
import logging

_logger = logging.getLogger(__name__)


class CorsController(http.Controller):
    @classmethod
    def _add_cors_headers(cls, response):
        origin = request.httprequest.headers.get('Origin', '')
        _logger.info(f"Request Origin: {origin}")

        allowed_origins = [
                                # Local
                                'http://localhost:3000',
                                'http://localhost:3001'
                                'http://192.168.1.158:3000',

                                # BO admin
                                'https://d2eetc9vbffnkr.cloudfront.net',
                                # BO resto
                                'https://restopro.menupro.tn',

                                # Clients
                                'https://stories.menupro.tn',
                                'https://labouffe.menupro.tn',
                                'https://bruschetta.menupro.tn',
                                'https://patchouli.menupro.tn',
                                'https://tabounafood.menupro.tn',
                                'https://caferesto180.menupro.tn',
                                'https://invictus.menupro.tn',

                                #Printer
                                'http://198.168.1.102:8069/hw_proxy/',
                                'http://198.168.1.102:8069/hw_proxy/default_printer_action',
                                'http://198.168.1.102:8069/hw_proxy',
                            ]

        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            _logger.warning(f"Origin not allowed: {origin}")
            return Response("Origin not allowed", status=403)

        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
        response.headers[
            'Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept, Authorization, Access-Control-Allow-Headers, Access-Control-Allow-Methods, Access-Control-Allow-Credentials, Access-Control-Allow-Origin, Cache-Control, X-Frame-Options'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '3600'
        _logger.info(f"CORS headers added: {response.headers}")
        return response

    @http.route('/<path:route>', type='http', auth='public', methods=['OPTIONS'], csrf=False)
    def cors_preflight(self, route):
        _logger.info(f"Received OPTIONS request for route: {route}")
        _logger.info(f"Request headers: {request.httprequest.headers}")
        response = Response(status=204)
        return self._add_cors_headers(response)
