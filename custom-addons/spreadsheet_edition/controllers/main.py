import logging
import json

from odoo import http
from odoo.http import request, content_disposition, Controller

logger = logging.getLogger(__name__)


class SpreadsheetController(Controller):


    @http.route('/spreadsheet/xlsx', type='http', auth="user", methods=["POST"])
    def get_xlsx_file(self, zip_name, files, **kw):
        files = json.loads(files)

        content = request.env['spreadsheet.mixin']._zip_xslx_files(files)
        headers = [
            ('Content-Length', len(content)),
            ('Content-Type', 'application/vnd.ms-excel'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Disposition', content_disposition(zip_name))
        ]

        response = request.make_response(content, headers)
        return response
