from odoo import http
from odoo.http import request
from markupsafe import Markup
import logging

_logger = logging.getLogger(__name__)

class MapController(http.Controller):
    @http.route('/report/html/odoo_forge_sale_map.map_view_template', type='http', auth="user")
    def map_view(self, map_record_id):
        map_record = request.env['map_storage'].browse(int(map_record_id))
        safe_html = Markup(map_record.map_html)
        return request.render('odoo_forge_sale_map.map_view_template', {
            'map_html': safe_html
        })