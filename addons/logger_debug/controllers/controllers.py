from odoo import http

import logging
_logger = logging.getLogger(__name__)


class LoggerDebug(http.Controller):
    @http.route('/logger_debug/logger_debug', auth='public')
    def index(self, **kw):
        _logger.info("Hello, world")
        _logger.debug("DEBUG Hello, world DEBUG")
        return "Hello, world"

#     @http.route('/logger_debug/logger_debug/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('logger_debug.listing', {
#             'root': '/logger_debug/logger_debug',
#             'objects': http.request.env['logger_debug.logger_debug'].search([]),
#         })

#     @http.route('/logger_debug/logger_debug/objects/<model("logger_debug.logger_debug"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('logger_debug.object', {
#             'object': obj
#         })

